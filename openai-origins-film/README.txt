向所有人 / A LIGHT FOR EVERYONE
OpenAI · 从一个研究理想到世界的对话

交付
  openai-a-light-for-everyone.mp4  完整影片，120 秒，1920×1080，30 fps，H.264 / AAC 立体声
  original-score.mp3             本次原创配乐，256 kbps
  captions.srt                   可编辑中文字幕（成片同时包含画面字幕）
  poster.jpg                     影片封面
  storyboard.jpg                 十章分镜总览
  story.json                     原创叙事、章节文案和一手史实来源
  timing.json                    实际旁白时长和时间线

制作
  视觉：新编写的 GLSL / Python 程序；56,000 粒子、25 组发光曲线、
        3D 形态插值、动态轨道、光晕、胶片微噪点、排版和字幕。
  配乐：新创作的 96 BPM 音乐；加法合成钢琴、和声铺底、琶音、低频脉冲，
        从 D 小调色彩过渡到大调结尾。
  音效：新合成的立体声掠过、低频冲击、星点和输入键音。
  旁白：Microsoft Edge zh-CN-YunxiNeural 合成中文男声。
  混音：48 kHz 立体声；旁白期间配乐自动闪避；目标综合响度 -16 LUFS。
  字体：系统 Noto Sans CJK 和 Lato，字体文件不包含在源文件包内。

内容范围
  历史部分选取 2015—2024 年关键节点，用于描绘起源和成长。
  2019 年组织结构仅描述当年情况，不代表当前组织结构。
  关于使命、愿景的内容应理解为宗旨与追求，不是已经实现的结果。
  抽象球体表示连接世界的网络；聊天内容为原创交互示意。
  史实链接与对应依据见 story.json。
  没有使用现成 skill，也没有参考既有视频或文案。官方原始公告仅用于事实核验。

本地播放
  直接使用本地视频播放器打开 openai-a-light-for-everyone.mp4。

重新制作（Linux）
  需要 Python 3.10+、FFmpeg / ffprobe、Mesa EGL 和上述系统字体。
  python -m venv --system-site-packages .venv
  .venv/bin/pip install -r requirements.txt
  .venv/bin/python make_voice.py     需要联网；已附旁白 WAV 时可跳过
  .venv/bin/python make_audio.py
  .venv/bin/python build.py --jobs 4

  build.py 将 4 段画面独立渲染并无缝拼接，写入章节标记和立体声母带。
  渲染预览：.venv/bin/python render.py --stills
  单段预览：.venv/bin/python render.py --start 59 --end 62 --output preview.mp4

工程文件
  render.py        原创动画渲染器与排版
  make_audio.py    原创作曲、声音合成、自动混音、字幕输出
  make_voice.py    中文合成旁白、语速适配
  build.py         渲染与成片封装
  audio/           独立音乐、音效、旁白及混音音轨

无需其他素材或旧项目模板。

GitHub 分发
  完整视频保存在本目录，并作为仓库 Release 附件分发，以避免 Git 单文件大小限制。
  原版视频没有重新压缩；其 SHA-256 见 release-assets.json。
  下载地址：https://github.com/Gin-Sin/ml-system-illustrations/releases/tag/openai-film-v1

  克隆仓库后，可在本目录运行：
  gh release download openai-film-v1 --repo Gin-Sin/ml-system-illustrations --pattern openai-a-light-for-everyone.mp4 --dir .

  本目录不接入现有 GitHub Pages 页面。
  源文件 ZIP 内含旁白文件；成片和独立配乐作为单独 Release 附件下载。
