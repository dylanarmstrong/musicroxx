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
  def __init__(self, song_id, artist, title, filename=""):
    self.song_id = song_id
    self.artist = artist
    self.album = album
    self.filename = filename

  def get_song_label(self, flags):
    if flags:
      if flags == SHOW_FILENAME:
        return '%s' % (self.filename)
      elif flags == SHOW_ARTIST:
        return '%s - %s' % (self.artist, self.title)
      else:
        return '%s' % (self.filename)

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

    self.songs = []

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
        QtCore.SIGNAL("triggered()"), self.highlight_song)

    # Playlist
    QtCore.QObject.connect(self.ui.playlist, \
        QtCore.SIGNAL("itemActivated(QListWidgetItem*)"), self.set_song)

    # Threads
    QtCore.QObject.connect(self.thread, self.thread.song_signal, \
        self.act_song)
    QtCore.QObject.connect(self.thread, self.thread.state_signal, \
        self.act_state)

    self.thread.start()

  def view_playlist(self):
    if self.ui.playlist.isVisible():
      self.ui.playlist.setVisible(False)
    else:
      self.ui.playlist.setVisible(True)

  def set_song(self, item):
    self.client.seek(0, int(item.data(QtCore.Qt.UserRole).toInt()[0]))

  #TODO: I'm sure this could be majorly cleaned up..
  def bind_list(self, force=False):
    i = 0
    for track in self.client.playlist():
      filename = track.split(': ')
      if force:
        self.ui.playlist.clear()
      possible_item = self.ui.playlist.findItems(filename[1], QtCore.Qt.MatchExactly)
      if not possible_item:
        item = QtGui.QListWidgetItem(filename[1])
        item.setData(QtCore.Qt.UserRole, i)
        item.setText(filename[1])
        self.ui.playlist.addItem(item)
      i = i + 1

  def highlight_song(self):
    i = 0
    for track in self.client.playlist():
      filename = track.split(': ')
      possible_item = self.ui.playlist.findItems(filename[1], QtCore.Qt.MatchExactly)
      if possible_item and i == int(self.song_id):
        possible_item[0].setSelected(True)
      i = i + 1

  def song_label(self, songnm):
    self.ui.songlb.setText(songnm)

  def song_seek(self, songseek):
    songseek_lst = songseek.split(':')
    song_length = int(songseek_lst[1])

    # Exception for when mpd is stopped
    try:
      songseek_prg = float(songseek_lst[0]) / float(songseek_lst[1]) * 100
    except ZeroDivisionError:
      songseek_prg = 0

    # Block signals so that seek doesn't misinterpet user actions
    self.ui.songprg.blockSignals(True)
    self.ui.songprg.setValue(songseek_prg)
    self.ui.songprg.blockSignals(False)

    # Set user readable song length
    pos = str(datetime.timedelta(seconds=int(songseek_lst[0])))
    length = str(datetime.timedelta(seconds=int(songseek_lst[1])))
    self.ui.songprg_num.setText('%s / %s' % (pos, length))

  def song_id(self, songid):
    self.song_id = songid

  def set_seek(self, songseek):
    pos = (songseek * self.song_length / 100)
    self.seek(pos)

  def state(self, state):
    self.ui.statusbar.showMessage("Status: %s" % (state))

class retrieve_information(QtCore.QThread):
  scheduler = sched.scheduler(time.time, time.sleep)

  def __init__(self, parent=None):
    QtCore.QThread.__init__(self, parent)

    self.client = MPD()

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
      song_seek = status['time']
    except KeyError:
      song_seek = "0:0"

    try:
      song_id = status['songid']
    except KeyError:
      song_id = 0

    try:
      state = status['state']
    except KeyError:
      state = 'error'

    song = Song(song_id, song_artist, song_title, song_filename)
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
