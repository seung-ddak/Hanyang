# Hanyang interview study

The latest textbook and web widget are at the repository root. Open desktop/Open-StudyWidget.cmd on Windows (Python 3.10+ with Tk), or run python run_web.py and keep the terminal open.

Theory, exercises, interview questions and notes have separate sections linked to the five widget buttons. Complete all five checks and press Unlock to open the next stage, regardless of the date.

Progress is stored separately in the private study-progress branch at progress/state.json. Windows uses Git Credential Manager; the Pages app uses a fine-grained GitHub token restricted to Hanyang with Contents read/write permission. Enter it under settings and press Connect and sync. The token stays in the current tab only.

Configure Pages yourself using the root static files. No deployment workflow is enabled by this update. Keep personal progress and tokens out of Pages files.

course.html is the latest study content. original.pdf and original-pages/ preserve the source as an appendix. full_guide.pdf is the reference PDF with the source appendix; the HTML contains the latest lesson layout.

Validation: cd desktop and run python -m unittest test_study -v.
