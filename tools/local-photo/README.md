# 로컬 사진 생성 (FLUX.1 schnell, 맥 미니)

맥 미니(M4 16GB)에서 FLUX.1 schnell 4비트 모델로 썸네일 사진을 생성해 저장소에 커밋한다. GitHub Actions 의 OpenAI API 호출을 대체한다.

## 작동 방식

1. content JSON 에 `photo_scene` 필드를 쓴다(영어 한 문장, 40~300자).
2. LaunchAgent(60초마다 실행)가 05:00~11:00(KST) 에 `make_photos.py` 를 실행한다.
3. 스크립트가 `photo_scene` 이 있고 `.photo.jpg` 가 없는 오늘 날짜 지문을 찾아 FLUX.1 로 생성한다.
4. `content/<lang>/<day>.photo.jpg` 로 커밋, push 한다.
5. GitHub Actions publish.yml 이 최대 8분 대기하다 파일이 도착하면 thumb.py 에서 그 사진을 사용한다.

생성된 사진은 1216x640 JPEG(품질 88)이고, 시드는 날짜+언어 조합의 SHA-256 에서 결정적으로 뽑는다.

## 설정 (맥 미니에서 한 번만 실행)

```bash
bash tools/local-photo/setup-mini.sh <저장소 절대경로> <FLUX 모델 디렉터리>
# 예시:
bash tools/local-photo/setup-mini.sh ~/repos/english-reading ~/models/flux-schnell-q4
```

스크립트가 하는 일:
- Apple Silicon 및 디스크 여유 공간 확인
- `uv` 미설치 시 공식 설치 명령어 안내 (직접 실행하도록 출력)
- `uv tool install mflux` 로 mflux 설치
- 저장소 클론 또는 업데이트, git push 권한 확인
- plist 생성 후 `launchctl bootstrap` 으로 LaunchAgent 등록

### FLUX 모델 취득

방법 1(빠름): MacBook Air 에서 scp 복사
```bash
scp -r /Users/wonsang/test/english-reading/design/local-thumb/models/schnell-q4 \
  mini-hostname:~/models/flux-schnell-q4
```

방법 2: Hugging Face 에서 직접 다운로드(~9GB, 시간 소요)
```bash
uvx hf auth login
mflux-save -m schnell -q 4 --path ~/models/flux-schnell-q4
```

### 잠자기 방지

시스템 설정 > 배터리/에너지 절약 > "전원 어댑터 연결 시 컴퓨터 자동으로 잠자기" 를 꺼 두세요.

## 로그 확인

```bash
tail -f ~/Library/Logs/read-photo.log
```

## 수동 테스트

dry-run 으로 실제 생성만 하고 git 조작 없이 결과를 `/tmp` 에 저장한다.

```bash
python3 tools/local-photo/make_photos.py --day 2026-10-31 --lang en --dry-run
```

생성된 파일: `/tmp/2026-10-31_en.photo.jpg`

특정 날짜, 특정 언어를 실제로 커밋/push 하려면 `--dry-run` 을 빼고 실행한다.

```bash
python3 tools/local-photo/make_photos.py --day 2026-10-31 --lang en
```

## 비활성화

```bash
launchctl bootout gui/$UID/com.wspace.read-photo
```

재활성화:
```bash
launchctl bootstrap gui/$UID ~/Library/LaunchAgents/com.wspace.read-photo.plist
```

## 환경 변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `FLUX_MODEL_DIR` | (필수) | 4비트 모델 디렉터리 경로 |
| `MFLUX_BIN` | `mflux-generate` | mflux-generate 실행 파일 경로 |
