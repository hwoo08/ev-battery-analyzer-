# 깃허브 업로드 & 웹사이트 배포 가이드

방법이 세 가지입니다. 편한 걸 하나만 고르면 됩니다.

| | 방법 A · 웹 드래그 | 방법 B · 깃허브 데스크탑 앱 | 방법 C · Git 명령어 |
|---|---|---|---|
| 설치 | 없음 | 앱 하나 | Git |
| 조작 | 마우스만 | 마우스만 | 명령어 5줄 |
| 수정 후 재업로드 | 파일 다시 올리기 | 버튼 두 번 | `git push` |
| 추천 | 딱 한 번만 올릴 때 | **계속 고칠 거면 이게 최고** | 개발 익숙해지면 |

앞으로 사이트를 계속 다듬을 거라면 **방법 B(깃허브 데스크탑 앱)** 를 추천합니다.

---

# 방법 A — 설치 없이 웹에서 올리기

## A-1. 압축 풀기

받은 `ev-battery-analyzer.zip`을 **압축 풀기(Extract All)** 합니다.
폴더를 열었을 때 이렇게 보여야 합니다:

```
index.html   assets   main.py   data   docs   output   README.md   .gitignore
```

> ⚠️ 만약 폴더 안에 `ev-battery-analyzer` 폴더가 또 있으면,
> 그 **안쪽** 폴더가 진짜입니다. 안쪽 폴더를 열어서 위 목록이 보이는지 확인하세요.

## A-2. 깃허브에 빈 저장소 만들기

1. <https://github.com/new> 접속 (로그인 필요)
2. **Repository name** 칸에 `ev-battery-analyzer` 입력
3. **Public** 선택 ← *꼭 Public. Private이면 무료 계정에서 사이트가 안 열립니다.*
4. 밑에 있는 체크박스 3개(Add a README / .gitignore / license)는 **전부 해제**
5. 초록색 **Create repository** 클릭

## A-3. 파일 끌어다 놓기

저장소가 만들어지면 빈 화면에 안내문이 나옵니다.

1. 그 화면에서 **uploading an existing file** 링크를 클릭
   (안 보이면 저장소 상단의 **Add file** → **Upload files**)
2. 탐색기에서 A-1의 폴더를 열고, **폴더 안의 내용물 전체를 선택**해서
   (`Ctrl + A`) 브라우저의 점선 영역으로 **끌어다 놓습니다**

   > ❗ 폴더 자체를 끌지 말고 **안에 있는 것들**을 끌어야 합니다.
   > `index.html`이 저장소 맨 위에 있어야 사이트가 열립니다.
   > `assets` 폴더는 폴더째로 같이 끌면 하위 파일까지 따라 올라갑니다.

3. 파일 목록이 다 뜨면 아래 **Commit changes** 클릭

업로드가 끝나면 저장소 목록에 `index.html`, `assets`, `main.py` … 가 보입니다.

> `.gitignore`처럼 점(`.`)으로 시작하는 파일은 탐색기에서 숨김 처리돼 안 보일 수 있습니다.
> 없어도 사이트는 정상 동작하니 그냥 넘어가도 됩니다.

## A-4. 사이트 켜기 (GitHub Pages)

1. 저장소 상단 **Settings** 탭 클릭
2. 왼쪽 메뉴 아래쪽 **Pages** 클릭
3. **Source** → `Deploy from a branch` 선택
4. **Branch** → 왼쪽 `main`, 오른쪽 `/ (root)` 선택 → **Save**
5. 1~2분 기다린 뒤 새로고침하면 위쪽에 주소가 뜹니다

```
https://Hwoo08.github.io/ev-battery-analyzer/
```

**이 주소가 포트폴리오에 넣을 링크입니다.**

## A-5. 나중에 수정할 때

1. 저장소에서 고치고 싶은 파일 클릭 (예: `index.html`)
2. 오른쪽 위 **연필 아이콘**(Edit this file) 클릭
3. 내용 고치고 아래 **Commit changes** 클릭

30초~1분이면 사이트에 반영됩니다.
파일을 통째로 바꿀 때는 **Add file → Upload files**로 같은 이름의 파일을 올리면 덮어써집니다.

---

# 방법 B — 깃허브 데스크탑 앱으로 올리기

명령어는 하나도 없습니다. 앱을 깔고 버튼만 누르면 됩니다.
한 번 연결해두면, 이후 파일을 고칠 때마다 **버튼 두 번**으로 사이트가 갱신됩니다.

## B-1. 앱 설치하고 로그인

1. <https://desktop.github.com> 접속 → **Download for Windows** 클릭
2. 내려받은 파일 실행 (설치 중 물어보는 것 없이 자동으로 끝납니다)
3. 앱이 열리면 **Sign in to GitHub.com** 클릭
4. 브라우저가 열리면서 로그인 → **Authorize** 클릭 → 앱으로 자동 복귀
5. 이름·이메일 확인 화면이 나오면 그냥 **Finish**

## B-2. 프로젝트 폴더 연결하기

1. 받은 zip을 압축 해제합니다. 폴더를 열었을 때 이렇게 보여야 합니다:

   ```
   index.html   assets   main.py   data   docs   output   README.md
   ```

   > 폴더 안에 같은 이름의 폴더가 또 있으면 **안쪽** 폴더가 진짜입니다.

2. 앱 왼쪽 위 **File** → **Add local repository...** 클릭
3. **Choose...** 를 눌러 위 폴더를 선택
4. *"This directory does not appear to be a Git repository"* 라는 안내가 뜹니다.
   당황하지 말고 그 문장 안의 파란 글씨 **create a repository** 를 클릭
5. 이름이 자동으로 `ev-battery-analyzer` 로 채워집니다. 그대로 두고
   맨 아래 **Create Repository** 클릭

## B-3. 첫 커밋 만들기

1. 왼쪽에 파일 목록이 쭉 뜹니다 (index.html, main.py, assets…)
2. 왼쪽 아래 **Summary** 칸에 아무 설명이나 입력

   ```
   EV 배터리 잔존가치 분석기 첫 업로드
   ```

3. 파란 버튼 **Commit to main** 클릭

> 이 단계는 "내 컴퓨터 안에 기록을 남기는" 것이라, 아직 깃허브에는 안 올라갔습니다.

## B-4. 깃허브에 올리기 (Publish)

1. 화면 가운데 또는 위쪽의 **Publish repository** 버튼 클릭
2. 창이 뜨면 **`Keep this code private` 체크를 반드시 해제**합니다

   > ⚠️ 이게 켜져 있으면 비공개 저장소가 되어 무료 계정에서는 사이트가 열리지 않습니다.

3. **Publish repository** 클릭

끝났습니다. 깃허브에 저장소가 만들어지고 파일이 전부 올라갑니다.
상단 메뉴 **Repository** → **View on GitHub** 를 누르면 브라우저로 확인할 수 있습니다.

## B-5. 사이트 켜기 (GitHub Pages)

여기부터는 브라우저에서 합니다.

1. 저장소 페이지 상단 **Settings** 탭
2. 왼쪽 메뉴 **Pages**
3. **Source** → `Deploy from a branch`
4. **Branch** → `main` / `/ (root)` → **Save**
5. 1~2분 뒤 새로고침하면 주소가 뜹니다

```
https://Hwoo08.github.io/ev-battery-analyzer/
```

## B-6. 수정한 내용 다시 올리기 (앞으로는 이것만 반복)

1. 컴퓨터에서 파일을 평소처럼 고치고 저장
2. 깃허브 데스크탑 앱을 열면 **바뀐 부분이 자동으로 표시**됩니다
3. Summary에 뭘 고쳤는지 짧게 적고 → **Commit to main**
4. 오른쪽 위 **Push origin** 클릭

30초~1분이면 사이트에 반영됩니다. 이게 방법 B의 진짜 장점입니다.

## 앱에서 자주 막히는 곳

| 증상 | 해결 |
|---|---|
| `Add local repository`에서 폴더 선택이 안 됨 | `index.html`이 **직접** 들어있는 폴더를 골라야 합니다. 상위 폴더 X |
| **Publish repository** 버튼이 안 보임 | B-3의 **Commit to main**을 아직 안 눌렀습니다 |
| 올렸는데 사이트가 404 | 저장소가 Private입니다. Settings → 맨 아래 **Change visibility** → Public으로 변경 |
| **Push origin**이 회색 | 커밋할 변경사항이 없습니다. 파일을 저장했는지 확인 |
| 파일이 몇 개 안 올라감 | `.gitignore`가 `output/` 폴더를 일부러 제외합니다. 정상입니다 |

---

# 방법 C — Git 명령어로 올리기

## C-1. Git 설치 확인

PowerShell에서:

```powershell
git --version
```

버전이 안 뜨면 <https://git-scm.com/download/win> 에서 설치 후
**PowerShell을 새로 열어서** 다시 확인하세요. 설치는 계속 "다음"만 눌러도 됩니다.

처음 한 번만 이름·이메일을 등록합니다:

```powershell
git config --global user.name "김현우"
git config --global user.email "seyeongjo48@gmail.com"
```

## C-2. 저장소 만들기

방법 A의 **A-2**와 동일합니다. (Public, 체크박스 전부 해제)

## C-3. 업로드

프로젝트 폴더로 이동합니다. `dir`로 `index.html`이 보이는지 꼭 확인하세요:

```powershell
cd C:\Users\seyeo\Downloads\ev-battery-analyzer
dir
```

`index.html`이 안 보이고 폴더 이름만 하나 보이면 한 겹 더 들어갑니다:

```powershell
cd ev-battery-analyzer
dir
```

`index.html`이 보이면 이제 업로드합니다:

```powershell
git init
git add .
git commit -m "EV 배터리 잔존가치 분석기: Python 엔진 + 웹사이트"
git branch -M main
git remote add origin https://github.com/Hwoo08/ev-battery-analyzer.git
git push -u origin main
```

로그인 창이 뜨면 **Sign in with your browser**를 누르면 됩니다.
(비밀번호를 터미널에 직접 입력하는 방식은 더 이상 지원되지 않습니다.)

## C-4. 사이트 켜기

방법 A의 **A-4**와 동일합니다.

## C-5. 수정한 내용 다시 올리기

```powershell
git add .
git commit -m "무엇을 바꿨는지 짧게"
git push
```

---

# 자주 나오는 오류

| 메시지 / 증상 | 해결 |
|---|---|
| Pages 주소가 **404** | ① 저장소가 Public인지 ② `index.html`이 저장소 **맨 위**에 있는지 ③ Branch가 `main / (root)`인지 ④ 2분 기다렸는지 |
| 사이트는 뜨는데 **디자인이 깨짐** | `assets` 폴더가 안 올라갔습니다. Add file → Upload files로 `assets` 폴더를 다시 올리세요 |
| `fatal: not a git repository` | 폴더를 잘못 잡았습니다. `dir`로 `index.html` 확인 후 `git init`부터 |
| `remote origin already exists` | `git remote set-url origin https://github.com/Hwoo08/ev-battery-analyzer.git` |
| `failed to push some refs` | 저장소 만들 때 README를 체크했을 때 발생. `git pull origin main --allow-unrelated-histories` 후 다시 push |
| `src refspec main does not match any` | 커밋을 안 했습니다. `git add .` → `git commit -m "..."` 먼저 |
| 업로드했는데 파일이 0개 | 폴더 자체를 끌었습니다. 폴더를 **열고** 안의 내용물을 끄세요 |

---

# 폴더 구조

```
ev-battery-analyzer/
├── index.html              ← 사이트 첫 페이지 (Pages가 이 파일을 읽음, 반드시 맨 위에)
├── assets/
│   ├── style.css
│   └── app.js              ← 웹 평가 엔진 (main.py와 동일 로직)
├── main.py                 ← 터미널 버전
├── data/battery_data.csv
├── docs/
│   ├── evaluation_method.md
│   └── github_deploy.md    ← 이 문서
├── output/                 ← 실행 결과 (git에는 올라가지 않음)
├── .gitignore
└── README.md
```
