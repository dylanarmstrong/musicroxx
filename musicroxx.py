#!/usr/bin/env python2

"""
Copyright (c) 2012 Dylan Armstrong

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

from PyQt4 import QtGui
from PyQt4 import QtCore
from ui.wind import Ui_MainWindow
import mpd, os, sys, time, sched, datetime, socket

# Global flags
SHOW_FILENAME = 0
SHOW_ARTIST = 1

# Song object to avoid unnecessary threading
class Song(object):
  def __init__(self, song_id, artist, title, filename, song_length):
    self.song_id = song_id
    self.artist = artist
    self.title = title
    self.filename = filename
    self.song_length = song_length

  def get_song_label(self, flags):
    if flags == SHOW_FILENAME:
      return '%s' % (self.filename)
    elif flags == SHOW_ARTIST:
      return '%s - %s' % (self.artist, self.title)
    else:
      return 'What are you trying to do - Developer'

  def get_length(self):
    return self.song_length.split(':')[1]

  def get_position(self):
    return self.song_length.split(':')[0]

# Handles all calls to MPD
class MPD(object):
  def __init__(self):
    self.client = mpd.MPDClient()

  def connect(self, i=0):
    try:
      self.client.connect("localhost", 6600)
    except mpd.ConnectionError, e:
      self.client.disconnect()
      if i < 5:
        self.connect(i + 1)
      else:
        print "Could not connect to MPD"
        exit(1)
    except socket.error:
      print "Could not connect to MPD"
      exit(1)

  def update_db(self):
    self.connect()
    self.client.update()

  def seek(self, pos, song_id):
    self.connect()
    self.client.seek(song_id, pos)

  def play(self):
    self.connect()
    self.client.play()

  def stop(self):
    self.connect()
    self.client.stop()

  def pause(self):
    self.connect()
    self.client.pause()

  def next(self):
    self.connect()
    self.client.next()

  def previous(self):
    self.connect()
    self.client.previous()

  def playlist(self):
    self.connect()
    return self.client.playlist()

  def currentsong(self):
    self.connect()
    return self.client.currentsong()

  def status(self):
    self.connect()
    return self.client.status()

class MainWindow(QtGui.QMainWindow):

  def __init__(self, parent=None):
    QtGui.QWidget.__init__(self, parent)

    self.client = MPD()

    self.ui = Ui_MainWindow()
    self.ui.setupUi(self)
    self.ui.playlist.setVisible(False)
    self.song_label_type = SHOW_FILENAME
    self.current_song = None

    self.init_signals()

  def init_signals(self):
    self.thread = retrieve_information()

    # Buttons
    QtCore.QObject.connect(self.ui.play, \
        QtCore.SIGNAL("clicked()"), self.client.play)
    QtCore.QObject.connect(self.ui.stop, \
        QtCore.SIGNAL("clicked()"), self.client.stop)
    QtCore.QObject.connect(self.ui.pause, \
        QtCore.SIGNAL("clicked()"), self.client.pause)
    QtCore.QObject.connect(self.ui.next, \
        QtCore.SIGNAL("clicked()"), self.client.next)
    QtCore.QObject.connect(self.ui.previous, \
        QtCore.SIGNAL("clicked()"), self.client.previous)
    QtCore.QObject.connect(self.ui.songprg, \
        QtCore.SIGNAL("valueChanged(int)"), self.set_seek)

    # Menu items
    QtCore.QObject.connect(self.ui.actionViewPlaylist, \
        QtCore.SIGNAL("triggered()"), self.view_playlist)
    QtCore.QObject.connect(self.ui.actionUpdateDB, \
        QtCore.SIGNAL("triggered()"), self.client.update_db)
    QtCore.QObject.connect(self.ui.actionViewCurrentSong,\
        QtCore.SIGNAL("triggered()"), self.highlight_current_song)

    # Playlist
    QtCore.QObject.connect(self.ui.playlist, \
        QtCore.SIGNAL("itemActivated(QListWidgetItem*)"), \
        self.set_current_song)

    # Threads
    QtCore.QObject.connect(self.thread, self.thread.song_signal, \
        self.act_song)
    QtCore.QObject.connect(self.thread, self.thread.state_signal, \
        self.act_state)

    self.thread.start()

  def act_song(self, song):
    # Song label
    if self.current_song is None or song.song_id != self.current_song.song_id:
      self.current_song = song
      self.ui.songlb.setText(song.get_song_label(self.song_label_type))

    # User readable song time
    song_length = str(datetime.timedelta(seconds=int(song.get_length())))
    current_pos = str(datetime.timedelta(seconds=int(song.get_position())))
    self.ui.songprg_num.setText('%s / %s' % (current_pos, song_length))

    # Seek bar
    try:
      song_seek_pos = float(song.get_position()) / \
          float(song.get_length()) * 100
    except ZeroDivisionError:
      song_seek_pos = 0

    # Block signals so that seek doesn't misinterpet user actions
    self.ui.songprg.blockSignals(True)
    self.ui.songprg.setValue(song_seek_pos)
    self.ui.songprg.blockSignals(False)


  #TODO: change state to more readable variation such as playing, paused, etc.
  def act_state(self, state):
    self.ui.statusbar.showMessage("Status: %s" % (state))

  #TODO: I'm sure this could be majorly cleaned up..
  def act_playlist(self, force=False):
    i = 0
    for track in self.client.playlist():
      filename = track.split(': ')
      if force:
        self.ui.playlist.clear()
      possible_item = self.ui.playlist.findItems(filename[1], \
          QtCore.Qt.MatchExactly)
      if not possible_item:
        item = QtGui.QListWidgetItem(filename[1])
        item.setData(QtCore.Qt.UserRole, i)
        item.setText(filename[1])
        self.ui.playlist.addItem(item)
      i = i + 1

  def view_playlist(self):
    if self.ui.playlist.isVisible():
      self.ui.playlist.setVisible(False)
    else:
      self.act_playlist()
      self.ui.playlist.setVisible(True)

  def highlight_current_song(self):
    i = 0
    for track in self.client.playlist():
      filename = track.split(': ')
      possible_item = self.ui.playlist.findItems(filename[1], \
          QtCore.Qt.MatchExactly)
      if possible_item and i == int(self.song_id):
        possible_item[0].setSelected(True)
      i = i + 1

  def set_current_song(self, item):
    self.set_seek(0, int(item.data(QtCore.Qt.UserRole).toInt()[0]))

  def set_seek(self, song_seek, song_id=None):
    self.client.seek((song_seek * int(self.current_song.get_length()) \
        / 100), song_id if song_id else self.current_song.song_id)

class retrieve_information(QtCore.QThread):
  scheduler = sched.scheduler(time.time, time.sleep)

  def __init__(self, parent=None):
    QtCore.QThread.__init__(self, parent)

    self.client = MPD()
    self.songs = []

    self.song_signal = QtCore.SIGNAL("song_thread")
    self.state_signal = QtCore.SIGNAL("state_thread")

    self.exiting = False

  def song_info(self):
    current_song = self.client.currentsong()
    status = self.client.status()

    try:
      song_artist = current_song['artist']
      song_title = current_song['title']
      song_filename = current_song['file']
    except KeyError:
      song_artist = "Unknown"
      song_title = "Unknown"
      song_filename = current_song['file']

    try:
      song_length = status['time']
    except KeyError:
      song_length = "0:0"

    try:
      song_id = status['songid']
    except KeyError:
      song_id = -1

    try:
      state = status['state']
    except KeyError:
      state = 'error'

    #TODO: add in tiny no overhead db to store this stuff
    song = Song(song_id, song_artist, song_title, song_filename, song_length)
    self.emit(self.song_signal, song)
    self.emit(self.state_signal, state)

  def timed_call(self, calls_per_second, callback, *args, **kw):
    period = 1.0 / calls_per_second
    def reload():
      callback(*args, **kw)
      self.scheduler.enter(period, 0, reload, ())
    self.scheduler.enter(period, 0, reload, ())

  def __del__(self):
    self.exiting = True
    self.wait()

  def run(self):
    self.timed_call(1.0, self.song_info)
    self.scheduler.run()

def main(args):
  app = QtGui.QApplication(sys.argv)
  window = MainWindow()
  window.show()
  window.raise_()
  sys.exit(app.exec_())

if __name__ == "__main__":
  main(sys.argv)
