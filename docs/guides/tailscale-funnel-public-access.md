# Karakeep 공개 접속 — Tailscale Funnel 셋업 가이드

5개 PC에서 각자 `localhost`로 Karakeep을 띄우던 구조를, **상시 호스트 1대 +
무료 공개 URL** 로 바꾸는 방법. 도메인 비용 0원, 어디서든 브라우저로 접속한다.

> 비밀(auth key·CA·tailnet 이름·회사명)은 이 문서에 적지 않는다. 그것들은
> gitignore 된 `.env` / `docker-compose.override.yml` / `certs/` / 개인 메모리에만
> 존재한다. 이 문서는 토폴로지와 구성 구조만 담는다. URL의 tailnet 부분은
> `<tailnet>`(예: `tailXXXXXX`)로 표기한다.

## 1. 왜 이 방식인가

### 해결하려는 문제
- 5대 PC가 각자 `localhost:3001`로 Karakeep을 실행 → **PC마다 SQLite DB가 분리**되어
  제각각 논다. Obsidian vault(markdown)+git으로 겨우 맞추는 상태였다.
- 한 대의 **공유 인스턴스**로 모으면 이 분열 자체가 사라진다.

### 왜 Vercel/Netlify는 안 되는가
Karakeep은 **상태를 가진 상시 컨테이너**다 — 영속 볼륨(SQLite + 스크린샷),
백그라운드 워커(크롤·AI 태깅 큐), 사이드카 `chrome` 컨테이너. 서버리스(Vercel)는
이 셋 다 불가. "컨테이너를 계속 돌리는 서버"가 필요하다.

### 왜 Tailscale Funnel인가
- **무료**, **도메인 불필요**, **고정 공개 URL**(`https://karakeep.<tailnet>.ts.net`).
- 호스트가 **아웃바운드**로만 연결 → 공개 IP·포트포워딩 불필요(NAT/방화벽 뒤 OK).
- 방문 기기엔 **클라이언트 설치 불필요** — 그냥 브라우저로 연다.
- 대안인 Cloudflare Tunnel은 본인 도메인(유료)이 필요해서 제외.

## 2. 아키텍처

```
[어디서든 브라우저] ─https─▶ Tailscale Funnel 인그레스 ─DERP/443─▶ tailscale 컨테이너
                                                                      │ serve proxy
                                                                      ▼
                                                              karakeep:3000 (앱)
```

- `tailscale` 컨테이너가 tailnet 노드("karakeep")로 합류 → Funnel로 공개.
- 같은 compose 네트워크(`karakeep_default`)에서 `http://karakeep:3000`으로 프록시.
- 호스트는 **Windows + WSL2**, Docker 상시 구동. 컨테이너 `restart: unless-stopped`
  덕분에 주간 리셋 후에도 같은 URL로 자동 복구(노드 키는 named volume에 영속).

## 3. 사내망(MITM) 고려 — 중요

이 호스트는 사내 방화벽이 HTTPS를 자체 루트 CA로 **MITM 재서명**하고 **UDP를
차단**한다([corporate-tls-mitm] 환경). 그래서:

1. **UDP(WireGuard) 차단** → Tailscale이 자동으로 **DERP relay(TCP 443)** 폴백.
   로그에 `netcheck: UDP is blocked, trying HTTPS` → `home is now derp-NN`.
2. **443 MITM** → Tailscale(Go)이 controlplane/DERP 핸드셰이크에서 **사내 CA를
   신뢰**해야 한다. 시스템 루트 + 사내 CA 결합 번들을 `SSL_CERT_FILE`로 주입.
3. DPI 차단 가능성은 있으나 **본 환경에서는 통과 확인됨**(컨트롤플레인 연결 +
   funnel 응답 200). 막히는 망이라면 Oracle 무료 VM 등 "공개 서버" 방식으로 선회.

## 4. 사전 준비 (Tailscale admin, 브라우저 1회)

1. **계정 생성** → <https://login.tailscale.com/start> (무료 Personal).
2. **HTTPS 인증서 켜기** → admin → DNS → MagicDNS ON + **Enable HTTPS**. (Funnel 필수)
3. **Funnel 권한** → admin → Access controls 정책 JSON에 추가:
   ```json
   "nodeAttrs": [
     { "target": ["autogroup:member"], "attr": ["funnel"] }
   ]
   ```
4. **인증키 발급** → admin → Settings → Keys → Generate auth key.
   **Ephemeral OFF**(노드/URL 영속), 태그 없음. `tskey-auth-…` 복사.
5. **[필수] 노드 키 만료 끄기** → 노드 합류 후 admin → Machines → `karakeep` →
   `⋯` → **Disable key expiry**. 안 하면 ~180일 뒤 키 만료로 funnel이 끊긴다.

## 5. 호스트 구성 (gitignore된 머신 로컬 파일)

### 5.1 사내 CA 결합 번들
```bash
cat /etc/ssl/certs/ca-certificates.crt certs/corp-ca.crt > certs/ca-bundle-with-corp.crt
```

### 5.2 `certs/tailscale-serve.json` (Funnel → 앱)
```json
{
  "TCP": { "443": { "HTTPS": true } },
  "Web": {
    "${TS_CERT_DOMAIN}:443": {
      "Handlers": { "/": { "Proxy": "http://karakeep:3000" } }
    }
  },
  "AllowFunnel": { "${TS_CERT_DOMAIN}:443": true }
}
```
`${TS_CERT_DOMAIN}`은 컨테이너가 노드 FQDN으로 자동 치환한다.

### 5.3 `docker-compose.override.yml`에 서비스 추가
```yaml
services:
  tailscale:
    image: tailscale/tailscale:latest
    profiles: ["tunnel"]            # 평소 up엔 안 뜸; --profile tunnel 일 때만 기동
    environment:
      TS_AUTHKEY: ${TS_AUTHKEY:-}
      TS_HOSTNAME: karakeep         # 노드 이름 = URL의 서브도메인
      TS_STATE_DIR: /var/lib/tailscale
      TS_SERVE_CONFIG: /config/serve.json
      SSL_CERT_FILE: /certs/ca-bundle-with-corp.crt   # 사내 MITM 신뢰용
    volumes:
      - tailscale-state:/var/lib/tailscale
      - ./certs/tailscale-serve.json:/config/serve.json:ro
      - ./certs:/certs:ro
    devices:
      - /dev/net/tun:/dev/net/tun
    cap_add: [NET_ADMIN]
    restart: unless-stopped

volumes:
  tailscale-state:
```

> ⚠️ **이름 충돌 주의**: 컨테이너 `hostname:`을 `karakeep`으로 두면 안 된다.
> `/etc/hosts`에서 `karakeep`→자기 자신으로 잡혀 serve 프록시가 앱 대신 tailscale
> 컨테이너를 찔러 **connection refused**가 난다. 노드 이름은 반드시 **`TS_HOSTNAME`**
> 으로만 지정한다.
>
> WSL2에서는 `/dev/net/tun` 초기화가 실패해 자동으로 **userspace networking**으로
> 떨어지는데, Funnel에는 문제없다.

### 5.4 `.env` (gitignore됨)
```
TS_AUTHKEY=tskey-auth-…                         # 최초 등록용(이후 state 볼륨이 유지)
DISABLE_SIGNUPS=true                            # 공개 노출 → 신규 가입 차단(필수)
NEXTAUTH_URL=https://karakeep.<tailnet>.ts.net  # 로그인 콜백을 공개 URL 기준으로
```

## 6. 기동 & 검증

```bash
# 1) 공개 전 보안 적용 (가입 차단 반영)
docker compose up -d karakeep

# 2) Funnel 기동
docker compose --profile tunnel up -d tailscale
docker logs -f karakeep-tailscale-1     # active login / DERP / "Funnel on: https://…" 확인

# 3) 종단 검증
curl -sSL https://karakeep.<tailnet>.ts.net      # → 200, /signin, <title>Karakeep</title>
docker exec karakeep-tailscale-1 tailscale funnel status
```

확인 포인트:
- 로그 `active login` + `home is now derp-NN` + `Funnel on: …`
- 공개 URL **HTTP 200** → `/signin`
- `/signup` 페이지에 "disabled" → 가입 차단 동작
- (선택) 폰을 **셀룰러**로 접속해 외부망 확인

## 7. 운영

| 작업 | 명령 |
|------|------|
| 끄기 | `docker compose --profile tunnel stop tailscale` |
| 켜기 | `docker compose --profile tunnel up -d tailscale` |
| URL 확인 | `docker exec karakeep-tailscale-1 tailscale funnel status` |
| 리셋 후 | 자동 복구(restart 정책 + state 볼륨) — 같은 URL |

5대 PC는 이제 각자 띄우지 말고 **이 URL을 북마크**해 단일 인스턴스를 공유한다.

## 8. 보안 메모

- 인터넷에 열려 있고 **유일한 관문이 Karakeep 로그인**이다(앞단 SSO 게이트 없음).
  → 강한 비밀번호 필수, `DISABLE_SIGNUPS=true` 필수.
- 더 높은 보안을 원하면 `serve.json`의 `AllowFunnel`을 빼고 **Tailscale Serve**
  (tailnet 전용)로 전환 가능 — 단 접속 기기마다 Tailscale 설치가 필요(트레이드오프).

## 9. 트러블슈팅

| 증상 | 원인 / 조치 |
|------|-------------|
| 공개 URL이 `Connection reset` | 백엔드 프록시 실패. tailscale 컨테이너 → `karakeep:3000` 도달 확인. |
| `karakeep:3000` connection refused | 컨테이너 `hostname: karakeep` 충돌. `TS_HOSTNAME`만 쓰고 `hostname:` 제거(§5.3). |
| 컨트롤플레인 `x509` 실패 | `SSL_CERT_FILE`에 사내 CA 결합 번들 누락(§5.1). |
| 한참 뒤 funnel 끊김 | 노드 키 만료. admin에서 **Disable key expiry**(§4-5). |
| `up`만 했는데 안 뜸 | `tailscale`은 profile `tunnel` — `--profile tunnel` 필요. |

[corporate-tls-mitm]: ../architecture/system/pc-environment.md
