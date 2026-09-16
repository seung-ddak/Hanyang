# 한양대 면접 공부 · 동기화 개정판

Windows 위젯과 브라우저 위젯에서 같은 완료 체크·수동 해금·메모를 사용합니다.

## 시작

- 기존 Windows: 위젯을 닫고 다운로드의 Hanyang-Study-Widget/Open-StudyWidget.cmd를 다시 실행합니다.
- 저장소를 새로 받은 Windows: desktop/Open-StudyWidget.cmd. Python 3.10 이상과 Tk가 필요합니다.
- Mac/Linux/Windows 브라우저: Python 3.10 이상에서 `python run_web.py`. 실행 중인 터미널을 유지합니다.
- GitHub Pages: 사용자 본인이 Pages를 설정한 뒤 해당 주소로 접속합니다. 이 작업에서는 Pages를 활성화하거나 배포하지 않았습니다.

## 학습 흐름

1. 교재 읽기 버튼은 해당 단계의 이론으로 이동합니다. 반복 사용하는 장은 날짜별 소제목 범위로 나뉩니다.
2. 아래에 문제 풀기 → 면접 준비 → 메모가 이어집니다. 각 버튼은 해당 구획으로 연결됩니다.
3. 다섯 항목을 모두 체크하면 다음 단계 해금 버튼이 활성화됩니다. 날짜와 관계없이 직접 해금합니다.
4. 이전 단계 체크를 취소하면 그 뒤 단계가 다시 잠깁니다. 기존 후속 기록은 삭제하지 않습니다.

## 기록 동기화

- 기록 저장소: seung-ddak/Hanyang, **비공개 유지**.
- 전용 브랜치: study-progress, 파일: progress/state.json. main 브랜치와 Pages 산출물에는 개인 기록을 포함하지 않습니다.
- Windows/로컬 웹 서버: Git Credential Manager의 기존 GitHub 로그인 또는 HANYANG_GITHUB_TOKEN 환경변수를 사용합니다. 시작 시와 실행 중 30초마다 동기화합니다.
- Pages 웹앱: 설정에서 해당 저장소만 선택한 fine-grained token(Contents 읽기·쓰기)을 입력하고 연결합니다. 토큰은 현재 탭 메모리에만 존재하므로 새 탭/재실행에서는 다시 입력합니다. 채팅이나 저장소에 토큰을 적지 마세요.
- 웹에서는 변경 후 자동 동기화하고, 연결 중에는 60초마다 확인합니다. 다른 기기에서 불러올 때 동기화 완료 표시를 확인하세요.
- 오프라인 기록은 기기에 남습니다. PC 종료 직전 변경이 아직 동기화되지 않았다면 다음 실행에서 재시도합니다.
- 체크는 항목별 최신 변경을 병합하여 체크 취소도 전달합니다. 메모는 수정 이력을 남기고 최신 20개를 화면에 표시합니다. 전체 기록은 백업 다운로드에 보존됩니다.
- GitHub 로그인을 브라우저에서 했다는 것만으로 Pages가 비공개 저장소 쓰기 권한을 얻지는 않습니다. 최초 연결 토큰이 필요합니다.

## Pages 설정 시 배포 범위

준비한 .github/workflows/pages.yml은 **수동 실행만** 하며 허용된 정적 파일만 배포합니다. Settings → Pages의 배포 소스를 GitHub Actions로 선택한 뒤 Actions에서 실행할 수 있습니다. 실제 사용 가능 여부는 계정/저장소의 Pages 제공 조건을 따릅니다.

별도 Pages 저장소를 쓴다면 index.html, app.js, progress.js, lesson_scope.js, reader.css, styles.css, course.html, lessons.html, study_schedule.json, manifest.webmanifest, sw.js, original.pdf, full_guide.pdf, assets/, original-pages/만 복사합니다. 기록 저장소 Hanyang은 비공개로 유지해야 합니다. Pages 사이트가 공개라면 배포한 교재와 원본 부록도 공개됩니다.

## 교재와 원본

- 최신 학습 본문: course.html / 위젯의 단계별 교재.
- 전체 참고 HTML: lessons.html. 맨 아래에 원본 16쪽 부록이 있습니다.
- original.pdf: 제공된 대학원면접대비속성자료PDF_231104_093456.pdf와 동일한 원본.
- full_guide.pdf: 기존 PDF 본문에 원본 16쪽을 추가한 참고판(원본 부록 90~105쪽). 이번 세부 보강 설명과 단계별 재배치는 HTML이 최신입니다.
- SOURCE_REVIEW.md: 원본 페이지별 대응, 보강 범위, 원문 오류·혼동 정정.

C 기초는 원본을 이해하기 위한 선수 학습이며 원본 중심 과목은 자료구조·정렬·탐색·OS·네트워크·객체지향·이산수학·DB입니다. 해시 함수 종류, Borůvka, 교체 정책, 추상 클래스/STL, 4NF/5NF 등을 해당 본문에 보강했습니다. 스캔 손글씨의 불명확한 기호는 임의로 복원하지 않았습니다.

## 검증

- Python: `cd desktop` 후 `python -m unittest test_study -v`.
- 49단계 DOM 구획·앵커·날짜별 범위·수동 해금·재잠금 자동 검증.
- 원본 16쪽 이미지 확인 및 PDF 부록의 첫/마지막 페이지 렌더 확인.
- 이 환경에서 연결 가능한 Browser/Computer Use가 없어 실제 브라우저 화면과 모바일 터치 동작의 최종 시각 검증은 수행하지 못했습니다.
