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
import mpd, os, sys, time, sched, datetime

class Song(object):
  def __init__(self, song_id, artist="", album="", filename=""):
    self.song_id = song_id
    self.artist = artist
    self.album = album
    self.filename = filename

class MainWindow(QtGui.QMainWindow):
  client = mpd.MPDClient()

  def __init__(self, parent=None):
    QtGui.QWidget.__init__(self, parent)

    self.ui = Ui_MainWindow()
    self.ui.setupUi(self)
    self.ui.playlist.setVisible(False)
    self.songs = []
    self.init_signals()

  def init_signals(self):
    self.thread = retrieve_information()

    #buttons
    QtCore.QObject.connect(self.ui.play, \
        QtCore.SIGNAL("clicked()"), self.play)
    QtCore.QObject.connect(self.ui.stop, \
        QtCore.SIGNAL("clicked()"), self.stop)
    QtCore.QObject.connect(self.ui.pause, \
        QtCore.SIGNAL("clicked()"), self.pause)
    QtCore.QObject.connect(self.ui.next, \
        QtCore.SIGNAL("clicked()"), self.next)
    QtCore.QObject.connect(self.ui.previous, \
        QtCore.SIGNAL("clicked()"), self.previous)
    QtCore.QObject.connect(self.ui.songprg, \
        QtCore.SIGNAL("valueChanged(int)"), self.set_seek)

    #menu items
    QtCore.QObject.connect(self.ui.actionViewPlaylist, \
        QtCore.SIGNAL("triggered()"), self.view_playlist)
    QtCore.QObject.connect(self.ui.actionUpdateDB, \
        QtCore.SIGNAL("triggered()"), self.update_db)
    QtCore.QObject.connect(self.ui.actionViewCurrentSong,\
        QtCore.SIGNAL("triggered()"), self.highlight_song)

    #playlist
    QtCore.QObject.connect(self.ui.playlist, \
        QtCore.SIGNAL("itemActivated(QListWidgetItem*)"), self.set_song)

    #threads
    QtCore.QObject.connect(self.thread, self.thread.songname_signal, \
        self.song_label)
    QtCore.QObject.connect(self.thread, self.thread.songseek_signal, \
        self.song_seek)
    QtCore.QObject.connect(self.thread, self.thread.songid_signal, \
        self.song_id)
    QtCore.QObject.connect(self.thread, self.thread.state_signal, \
        self.state)
    QtCore.QObject.connect(self.thread, self.thread.playlist_signal, \
        self.bind_list)

    self.thread.start()
  def update_db(self):
    self.connect()
    self.client.update()

  def view_playlist(self):
    if self.ui.playlist.isVisible():
      self.ui.playlist.setVisible(False)
    else:
      self.ui.playlist.setVisible(True)

  def set_song(self, item):
    self.seek(0, int(item.data(QtCore.Qt.UserRole).toInt()[0]))

  def bind_list(self, force=False):
    self.connect()
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
    self.connect()
    i = 0
    for track in self.client.playlist():
      filename = track.split(': ')
      possible_item = self.ui.playlist.findItems(filename[1], QtCore.Qt.MatchExactly)
      if possible_item and i == int(self.song_id):
        possible_item[0].setSelected(True)
      i = i + 1

  def song_label(self, songnm):
    self.connect()
    self.ui.songlb.setText(songnm)

  def song_seek(self, songseek):
    self.connect()
    songseek_lst = songseek.split(':')
    self.song_length = int(songseek_lst[1])

    try:
      songseek_prg = float(songseek_lst[0]) / float(songseek_lst[1]) * 100
    except ZeroDivisionError:
      songseek_prg = 0

    self.ui.songprg.blockSignals(True)
    self.ui.songprg.setValue(songseek_prg)
    self.ui.songprg.blockSignals(False)

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

  def connect(self):
    try:
      self.client.connect("localhost", 6600)
    except mpd.ConnectionError, e:
      self.client.disconnect()
      self.client.connect("localhost", 6600)

  def seek(self, pos, _song_id=-1):
    if _song_id == -1:
      _song_id = self.song_id
    self.connect()
    self.client.seek(_song_id, pos)

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
    self.songid = -1
    self.song_length = -1
    self.client.next()

  def previous(self):
    self.connect()
    self.songid = -1
    self.song_length = -1
    self.client.previous()

class retrieve_information(QtCore.QThread):
  client = mpd.MPDClient()
  scheduler = sched.scheduler(time.time, time.sleep)

  def __init__(self, parent=None):
    QtCore.QThread.__init__(self, parent)

    self.songname_signal = QtCore.SIGNAL("songnm_thread")
    self.songseek_signal = QtCore.SIGNAL("songlen_thread")
    self.songid_signal = QtCore.SIGNAL("songid_thread")
    self.state_signal = QtCore.SIGNAL("state_thread")
    self.playlist_signal = QtCore.SIGNAL("playlist_thread")

    self.exiting = False

  def connect(self):
    try:
      self.client.connect("localhost", 6600)
    except mpd.ConnectionError, e:
      pass

  def song_info(self):
    self.connect()
    song = self.client.currentsong()
    status = self.client.status()
    try:
      songnm = '%s - %s' % (song['artist'], song['title'])
    except KeyError:
      songnm = song['file']

    try:
      songseek = status['time']
    except KeyError:
      songseek = "0:0"

    try:
      songid = status['songid']
    except KeyError:
      songid = 0

    try:
      state = status['state']
    except KeyError:
      state = 'error'

    self.emit(self.songname_signal, songnm)
    self.emit(self.songseek_signal, songseek)
    self.emit(self.songid_signal, songid)
    self.emit(self.state_signal, state)
    self.emit(self.playlist_signal)
    return songnm

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
