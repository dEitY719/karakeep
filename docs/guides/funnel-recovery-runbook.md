# Funnel 복구 Runbook (external PC 전용)

internal PC 에서 접속 불가(`NXDOMAIN` / proxy `502 notresolvable`)가 발생했을 때,
**Karakeep 호스트(external PC)** 에서 이 순서대로만 실행하면 된다.

> internal 쪽 경로(사내 proxy env, cron)는 이미 internal PC 에서 수정 완료.
> 이 runbook 은 funnel 공개만 복구하면 양쪽이 모두 즉시 회복된다.

셋업 전반(구성·보안·운영)은 [Tailscale Funnel 셋업 가이드](tailscale-funnel-public-access.md)를 본다.
아래 `<tailnet>` 은 실제 tailnet 이름으로, `<karakeep repo>` 는 각 PC 의 karakeep clone 경로로 바꿔 읽는다.

## 배경 — 왜 NXDOMAIN 이 되는가

- **Funnel 비활성 시 호스트명은 공개 DNS(ts.net 권한 NS)에서 사라지고 MagicDNS(tailnet 내부) 전용으로 돌아간다.**
  그래서 tailnet 멤버(external PC)에서는 "정상"이고, 그 외 모든 망(사내 포함)에서는 존재하지 않는 주소가 된다.
- **재발 트리거**: funnel 컨테이너가 `profile: tunnel` 이라 **평범한 `docker compose up -d` 만으로는 기동되지 않는다.**
  `restart: unless-stopped` 는 명시적 `stop` 후이거나 컨테이너가 재생성된 경우(WSL 재생성 등)에는 복구해 주지 않는다.
- 2차 문제: internal cron(sync)이 사내 proxy env 없이 direct egress 를 시도해 방화벽 RST 가 났다
  (internal PC 에서 수정 완료).

## 0. 사망 판정 (아무 PC 에서나 30초)

```bash
curl -sS "https://dns.google/resolve?name=karakeep.<tailnet>.ts.net&type=A"
```

- `"Status":3` (NXDOMAIN) → **funnel 이 공개 DNS 에 없음 = 이 runbook 대상.** 아래로 진행.
- `Answer` 에 IP 가 있으면 → funnel 은 살아 있고 다른 문제(사내 망·인증).
  [funnel 가이드 §9 트러블슈팅 표](tailscale-funnel-public-access.md#9-트러블슈팅) 참고.

## 1. 컨테이너 재기동 — 가장 흔한 원인

```bash
cd <karakeep repo>                     # external PC 의 karakeep clone 위치
docker compose --profile tunnel up -d tailscale
docker logs --tail 50 karakeep-tailscale-1
```

성공 판정: 로그에 `active login` → `home is now derp-NN` → **`Funnel on: https://karakeep.<tailnet>.ts.net`**.

## 2. 로그에 key 만료가 보이면 (약 180일 주기)

로그에 `key expired` / 재인증 안내가 있으면:

1. <https://login.tailscale.com> → admin → Machines → `karakeep` → `⋯` →
   **Disable key expiry** (다시 안 끊기게 — 이걸 안 걸면 주기적 재발).
2. admin → Settings → Keys → auth key 발급 (**Ephemeral OFF**).
3. `.env` 의 `TS_AUTHKEY` 갱신 후:
   ```bash
   docker compose --profile tunnel up -d --force-recreate tailscale
   ```

## 3. 종단 검증

```bash
# external PC 는 tailnet 멤버라 MagicDNS 로 풀린다 — 컨테이너 정상 여부만 보여줄 뿐 공개 경로는 증명하지 않는다.
# 공개 경로는 §0 의 dns.google 조회(Answer 에 IP 복귀)와 아래 internal PC 확인으로 판정한다.
curl -sSL https://karakeep.<tailnet>.ts.net        # → 200, /signin, <title>Karakeep</title>
docker exec karakeep-tailscale-1 tailscale funnel status
```

그 다음 **internal PC** 에서:

```bash
set -a; . ~/.config/karakeep/proxy.env; . <karakeep repo>/.env; set +a
curl -sS -o /dev/null -w '%{http_code}\n' "$NEXTAUTH_URL"   # 200/401 이면 끝. 502 notresolvable = 아직 DNS 미전파, 수 분 대기
# (선택) cron 은 다음 정각/30분 실행에 자동 회복된다. 즉시 확인하려면 같은 셸에서:
<karakeep repo>/sync/.venv/bin/karakeep-sync auto
```

## 4. 여전히 안 되면

| 증상 | 조치 |
|------|------|
| `Funnel on` 로그는 있는데 공개 DNS 여전히 NXDOMAIN | 수 분 대기(DNS 전파). 그래도 안 되면 admin → DNS → MagicDNS ON + **Enable HTTPS** 확인 |
| 공개 URL `Connection reset` | 백엔드 프록시 실패(`karakeep:3000` connection refused) — 컨테이너 `hostname: karakeep` 충돌 아닌지 확인 |
| 컨트롤플레인 `x509` 실패 | `SSL_CERT_FILE` 사내 CA 결합 번들 누락 |
| 사내 프록시가 ts.net 자체를 차단 | 같은 tailscale 계열 도메인(login.tailscale.com)이 통과 실적이 있으므로 드물다. 발생 시 SR 등록 또는 Cloudflare Tunnel 선회 |

## 체크리스트

- [ ] external PC 에서 runbook §1 실행 (`--profile tunnel` 재기동)
- [ ] 필요시 §2 (key 만료 조치 + Disable key expiry)
- [ ] §3 종단 검증: 공개 DNS 에 IP 복귀 + internal 브라우저 접속 회복
