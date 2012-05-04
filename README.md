Python2 + PyQt4 + MPD Client

This is currently in an alpha state. There shouldn't be any crippling bugs, but not all the functionality that I'd like is quite there yet. It has a working library and songs can be added to the playlist all the while with the keybindings of ncmpcpp. It's not as advanced as something like ncmpcpp, but will be able to do much more as far as finding what you want and being out of your way as a music player. This is designed to be a simple music player, and I hope you enjoy it :)

To run, simply execute ./musicroxx.

To install:
```
# mkdir ~/bin
# vim (or a text editor of your choice) ~/bin/musicroxx
```
```bash
#!/bin/sh
cd $HOME/<path/to/musicroxx>
./musicroxx
```
```
# export PATH = $PATH:/home/<username>/bin
# hash -r
# musicroxx
```
You should add the path line to your zshrc/bashrc file. After that you can just run musicroxx like a normal program.

Here's a couple quick screenshots of musicroxx in action:
![screenshot.png](https://github.com/meinhimmel/musicroxx/raw/master/screenshot.png "Screenshot")

musicroxx; an opensource mpd client
Copyright (C) 2012  Dylan Armstrong

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
