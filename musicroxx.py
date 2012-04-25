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
import mpd, os, sys, time, sched, datetime, socket, signal

# Global flags
SHOW_FILENAME = 0
SHOW_ARTIST = 1

# Song object to avoid unnecessary threading
class Song(object):
  def __init__(self, song_id=None, artist=None, title=None, \
      filename=None, song_length=None):
    self.song_id = song_id
    self.artist = artist
    self.title = title
    self.filename = filename
    self.song_length = song_length

  def get_song_label(self, flags):
    if flags == SHOW_FILENAME:
      return '%s' % (self.filename)
    elif flags == SHOW_ARTIST:
      if self.artist and self.title:
        return '%s - %s' % (self.artist, self.title)
      else:
        return '%s' % (self.filename)
    else:
      return 'What are you trying to do - Developer'

  def get_length(self):
    return self.song_length.split(':')[1]

  def get_position(self):
    return self.song_length.split(':')[0]

class State(object):
  def __init__(self, mpd_state, random, repeat_all):
    self.mpd_state = mpd_state
    self.random = random
    self.repeat_all = repeat_all

# Handles all calls to MPD
class MPD(object):
  def __init__(self, host, port):
    self.client = mpd.MPDClient()
    self.host = host
    self.port = port

  def connect(self, i=0):
    try:
      self.client.connect(self.host, self.port)
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

  def toggle_repeat_all(self, state):
    self.connect()
    if state.repeat_all:
      state.repeat_all = 0
      self.client.repeat(0)
    else:
      state.repeat_all = 1
      self.client.repeat(1)

  def toggle_random(self, state):
    self.connect()
    if state.random:
      state.random = 0
      self.client.random(0)
    else:
      state.random = 1
      self.client.random(1)

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

  def listall(self):
    self.connect()
    return self.client.listall()

  def add(self, filename):
    self.connect()
    self.client.add(filename)

# Library nodes for directories
class Node(object):
  def __init__(self):
    self.dirs = {}
    self.files = []

class MainWindow(QtGui.QMainWindow):

  def __init__(self, config, parent=None):
    QtGui.QWidget.__init__(self, parent)

    self.config = config
    host = self.config.get_config_for('host')
    port = self.config.get_config_for('port')
    self.client = MPD(host, port)

    self.ui = Ui_MainWindow()
    self.ui.setupUi(self)
    self.set_keybindings()

    self.current_song = None
    self.current_state = None

    self.thread_song = retrieve_song_information(host, port)
    self.thread_library = retrieve_library(host, port)

    self.init_signals()

  def set_keybindings(self):
    keys = {}
    keys[0] = self.config.get_config_for('play')
    keys[1] = self.config.get_config_for('pause')
    keys[2] = self.config.get_config_for('stop')
    keys[3] = self.config.get_config_for('next')
    keys[4] = self.config.get_config_for('prev')
    keys[5] = self.config.get_config_for('repeat')
    keys[6] = self.config.get_config_for('random')
    keys[7] = self.config.get_config_for('add')
    keys[8] = self.config.get_config_for('remove')
    keys[9] = self.config.get_config_for('update_db')
    keys[10] = self.config.get_config_for('current_song')
    keys[11] = self.config.get_config_for('view_playlist')
    keys[12] = self.config.get_config_for('view_library')
    keys[13] = self.config.get_config_for('quit')

    actions = {}
    actions[0] = self.ui.actionPlay
    actions[1] = self.ui.actionPause
    actions[2] = self.ui.actionStop
    actions[3] = self.ui.actionNext
    actions[4] = self.ui.actionPrevious
    actions[5] = self.ui.actionRepeatAll
    actions[6] = self.ui.actionRandom
    actions[7] = self.ui.actionAdd
    actions[8] = self.ui.actionRemove
    actions[9] = self.ui.actionUpdateDB
    actions[10] = self.ui.actionViewCurrentSong
    actions[11] = self.ui.actionViewPlaylist
    actions[12] = self.ui.actionViewLibrary
    actions[13] = self.ui.actionQuit

    for k in keys:
      self.set_shortcut(actions[k], keys[k])

  def set_shortcut(self, action, keyseq):
    if keyseq:
      action.setShortcut(QtGui.QKeySequence(keyseq))

  def init_signals(self):
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
        QtCore.SIGNAL("triggered()"), self.act_playlist)
    QtCore.QObject.connect(self.ui.actionUpdateDB, \
        QtCore.SIGNAL("triggered()"), self.update_db)
    QtCore.QObject.connect(self.ui.actionViewCurrentSong, \
        QtCore.SIGNAL("triggered()"), self.highlight_current_song)
    QtCore.QObject.connect(self.ui.actionRepeatAll, \
        QtCore.SIGNAL("triggered()"), self.toggle_repeat_all)
    QtCore.QObject.connect(self.ui.actionRandom, \
        QtCore.SIGNAL("triggered()"), self.toggle_random)

    # Menu items same as buttons
    QtCore.QObject.connect(self.ui.actionPlay, \
        QtCore.SIGNAL("triggered()"), self.client.play)
    QtCore.QObject.connect(self.ui.actionStop, \
        QtCore.SIGNAL("triggered()"), self.client.stop)
    QtCore.QObject.connect(self.ui.actionPause, \
        QtCore.SIGNAL("triggered()"), self.client.pause)
    QtCore.QObject.connect(self.ui.actionNext, \
        QtCore.SIGNAL("triggered()"), self.client.next)
    QtCore.QObject.connect(self.ui.actionPrevious, \
        QtCore.SIGNAL("triggered()"), self.client.previous)

    # Playlist
    QtCore.QObject.connect(self.ui.playlist, \
        QtCore.SIGNAL("itemActivated(QListWidgetItem*)"), \
        self.set_current_song)
    self.ui.playlist.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
    self.connect(self.ui.playlist, \
        QtCore.SIGNAL('customContextMenuRequested(QPoint)'), \
        self.playlist_context_menu)

    # Library
    QtCore.QObject.connect(self.ui.library, \
        QtCore.SIGNAL("itemActivated(QTreeWidgetItem*, int)"), \
        self.add_playlist_song)

    # Song threads
    QtCore.QObject.connect(self.thread_song, self.thread_song.song_signal, \
        self.act_song)
    QtCore.QObject.connect(self.thread_song, self.thread_song.state_signal, \
        self.act_state)

    # Library threads
    QtCore.QObject.connect(self.thread_library, \
        self.thread_library.library_signal, self.act_library)

    self.thread_song.start()
    self.thread_library.start()

    self.act_playlist()

  def update_db(self):
    self.client.update_db()
    self.thread_library.update()

  def add_playlist_song(self, item, column):
    p = item.parent()
    filename_lst = []
    filename_real_lst = []
    while p != None:
        filename_lst.append(str(p.text(column)))
        p = p.parent()
    filename_lst.reverse()
    filename_lst.append(str(item.text(column)))
    filename = '/'.join(filename_lst)
    self.client.add(filename)
    self.act_playlist()

  def toggle_repeat_all(self):
    self.client.toggle_repeat_all(self.current_state)

  def toggle_random(self):
    self.client.toggle_random(self.current_state)

  def act_song(self, song):
    # Song label
    if self.current_song is None or song.song_id != self.current_song.song_id:
      self.current_song = song
      song_display_config = self.config.get_config_for('display')
      if song_display_config:
        if song_display_config == 'artist':
          song_display = SHOW_ARTIST
        else:
          song_display = SHOW_FILENAME
      else:
        song_display = SHOW_FILENAME
      self.ui.songlb.setText(self.current_song.get_song_label(song_display))

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
    self.current_state = state

    if state.repeat_all:
      repeat_all = "On"
      self.ui.actionRepeatAll.setChecked(True)
    else:
      repeat_all = "Off"
      self.ui.actionRepeatAll.setChecked(False)

    if state.random:
      random = "On"
      self.ui.actionRandom.setChecked(True)
    else:
      random = "Off"
      self.ui.actionRandom.setChecked(False)

    mpd_state = state.mpd_state
    if mpd_state == 'play':
      mpd_state = 'Playing'
    elif mpd_state == 'pause':
      mpd_state = 'Paused'
    elif mpd_state == 'stop':
      mpd_state = 'Stopped'

    #TODO: Status bar text is randomly disappearing on menu actions.. why?
    status = 'Status: %s | Random: %s | Repeat All: %s' % (mpd_state, \
        random, repeat_all)

    self.ui.statusbar.showMessage(status)

  #TODO: This looks messsy
  def act_library(self, songs):
    old_directory = None
    folder_name = ''

    old_item = None
    old_folder_name = ''
    old_child = None
    for song in songs:
      # Split paths into directories
      [sp for _,sp in sorted(
        (len(splitpath), splitpath) for splitpath in
        (path.split('/') for path in song.filename.split(': '))
        )
      ]

      if sp[0] == folder_name:
        item = old_item
      else:
        item = QtGui.QTreeWidgetItem([sp[0]])
        old_item = item
        folder_name = sp[0]

      parent = item
      for d in range(1,len(sp) - 1):
        if sp[d] == old_folder_name:
          child = old_child
        else:
          child = QtGui.QTreeWidgetItem([sp[d]])
          parent.addChild(child)
          old_child = child
          old_folder_name = sp[d]

        parent = child

      for d in range(len(sp) - 1,len(sp)):
        child = QtGui.QTreeWidgetItem([sp[d]])
        parent.addChild(child)

      self.ui.library.addTopLevelItem(item)

  #TODO: I'm sure this could be majorly cleaned up..
  def act_playlist(self, force=False):
    i = 0
    for song in self.client.playlist():
      filename = song.split(': ')
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

  def playlist_context_menu(self, point):
    menu = QtGui.QMenu(self)
    menu.addAction("Play")
    menu.addAction("Remove")
    menu.popup(self.ui.playlist.mapToGlobal(point))

  #TODO: Switch tabs instead of hiding/showing the playlist & same with lib
  #def view_playlist(self):
    #if self.ui.playlist.isVisible():
    #  self.ui.playlist.setVisible(False)
    #else:
    #  self.act_playlist()
    #  self.ui.playlist.setVisible(True)

  def highlight_current_song(self):
    i = 0
    for track in self.client.playlist():
      filename = track.split(': ')
      possible_item = self.ui.playlist.findItems(filename[1], \
          QtCore.Qt.MatchExactly)
      if possible_item and i == int(self.current_song.song_id):
        possible_item[0].setSelected(True)
      i = i + 1

  def set_current_song(self, item):
    self.set_seek(0, int(item.data(QtCore.Qt.UserRole).toInt()[0]))

  def set_seek(self, song_seek, song_id=None):
    if self.current_song:
      self.client.seek((song_seek * int(self.current_song.get_length()) \
        / 100), song_id if song_id else self.current_song.song_id)
    else:
      self.client.seek(0, song_id)

class retrieve_library(QtCore.QThread):
  scheduler = sched.scheduler(time.time, time.sleep)

  def __init__(self, host, port, parent=None):
    QtCore.QThread.__init__(self, parent)

    self.client = MPD(host, port)

    self.library_signal = QtCore.SIGNAL("library_thread")

    self.exiting = False

  def library_info(self):
    library = self.client.listall()

    if library != {}:
      songs = []
      for song in library:
        try:
          song_filename = song['file']
          song = Song(filename=song_filename)
          songs.append(song)
        except KeyError:
          pass
      self.emit(self.library_signal, songs)

  def __del__(self):
    self.exiting = True
    self.wait()

  def update(self):
    pass

  def run(self):
    self.library_info()
    #self.timed_call(1.0, self.library_info)
    self.scheduler.run()


class retrieve_song_information(QtCore.QThread):
  scheduler = sched.scheduler(time.time, time.sleep)

  def __init__(self, host, port, parent=None):
    QtCore.QThread.__init__(self, parent)

    self.client = MPD(host, port)

    self.song_signal = QtCore.SIGNAL("song_thread")
    self.state_signal = QtCore.SIGNAL("state_thread")

    self.exiting = False

  def song_info(self):
    current_song = self.client.currentsong()
    status = self.client.status()
    if current_song != {}:
      try:
        song_artist = current_song['artist']
        song_title = current_song['title']
      except KeyError:
        song_artist = None
        song_title = None

      song_filename = current_song['file']

      try:
        song_length = status['time']
      except KeyError:
        song_length = "0:0"

      try:
        song_id = current_song['pos']
      except KeyError:
        song_id = -1

      try:
        mpd_state = status['state']
        repeat_all = int(status['repeat'])
        random = int(status['random'])
      except KeyError:
        mpd_state = 'error'
        repeat_all = False
        random = False

      #TODO: add in tiny no overhead db to store this stuff
      song = Song(song_id, song_artist, song_title, song_filename, song_length)
      state = State(mpd_state, random, repeat_all)
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

class Config(object):
  def __init__(self):
    configpath = self._config_dir()
    self.make_config(configpath)
    self.config = self.parse_config(configpath)

  def get_config_for(self, name):
    try:
      option = self.config[name]
    except KeyError, e:
      option = None
    return option

  def _config_dir(self):
    if 'XDG_CONFIG_HOME' in os.environ:
      confighome = os.environ['XDG_CONFIG_HOME']
    else:
      confighome = os.path.join(os.environ['HOME'], '.config')
    return os.path.join(confighome, 'musicroxx')

  def make_config(self, configpath):
    try:
      os.makedirs(configpath)
    except OSError:
      pass
    configfile = os.path.join(configpath, 'config')
    if not os.path.isfile(configfile):
      from shutil import copyfile
      copyfile('./pkg/config', configfile)

  def parse_config(self, configpath):
    options = {}
    try:
      f = open(os.path.join(configpath, 'config'))
    except IOError:
      print 'File does not exist'
    config = {}
    for line in f:
      line = ''.join(e for e in line if not e.isspace())
      if not line.startswith('#'):
        key = line.split('=')
        try:
          config[key[0]] = key[1]
        except IndexError:
          pass
    f.close()
    return config

def main(args):
  config = Config()
  app = QtGui.QApplication(sys.argv)
  window = MainWindow(config=config)
  window.show()
  window.raise_()
  sys.exit(app.exec_())

if __name__ == "__main__":
  signal.signal(signal.SIGINT, signal.SIG_DFL)
  main(sys.argv)
