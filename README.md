# Back-To-Work
Timer that shows your real active time while working.


## I think I've seen this before...
This timer is based on Neil Cicierega's Work https://neilblr.com/post/58757345346
I wanted to an image to be shown while inactive, but editing their code was too much trouble for my inexperienced brain. 
AutoHotKey kept giving false positives after compiling the code, and I thought that would scare people, so I decided to remake the whole thing on Python.
I used chatgpt for this, so this code might be a mess but it works.


## Installation
pyinstaller --onefile --icon=app_icon.ico your_script.py


## How to use
- Open Back To Work.exe.
- Open the MENU, select one of the three "Program" slots.
- Click on the program/window you want to be linked to the timer.
- The timer will only move while you are active on a linked program.
- Use "Resume Previous Timer" to continue from the same time you had when the last time the timer was closed.
- Use "Reset Timer" to get the timer to zero (You can still resume your previous time).
- You can use any other image just by renaming it "maia.png" and having it on the same folder as the .exe.

## Credits 
- Original timer:
  Neil Cicierega
  https://neilblr.com
- Vtuber in the meme:
  Ichika Maia
  https://x.com/ichikamaia | https://www.twitch.tv/maia | https://www.youtube.com/channel/UCuKuBKEK3YIVgWW_2KJ4Htw
- Meme:
  maplesights
  https://x.com/maplesights
