from __future__ import absolute_import

import logging
import os

import gflags
import sqlite3


FLAGS = gflags.FLAGS
gflags.DEFINE_string('kvs_sqlite_path', './db',
                     'sqlite path')


class Store(object):
  """.Keeper implementation in SQLite, mostly for in-memory testing."""
  _conn = {} # class variable

  def __init__(self, prefix):
      self.prefix = prefix

  @property
  def conn(self):
      prefix = FLAGS.kvs_prefix + self.prefix
      if prefix not in self.__class__._conn:
          logging.debug('no sqlite connection (%s), making new', prefix)
          if FLAGS.kvs_sqlite_path != ':memory:':
              try:
                  os.mkdir(FLAGS.kvs_sqlite_path)
              except Exception:
                  pass
              conn = sqlite3.connect(os.path.join(
                  FLAGS.kvs_sqlite_path, '%s.sqlite' % prefix))
          else:
              conn = sqlite3.connect(':memory:')

          c = conn.cursor()
          try:
              c.execute('''CREATE TABLE data (item text, value text)''')
              conn.commit()
          except Exception:
              logging.exception('create table failed')
          finally:
              c.close()

          self.__class__._conn[prefix] = conn

      return self.__class__._conn[prefix]

  def get(self, item):
      #logging.debug('sqlite getting %s', item)
      result = None
      c = self.conn.cursor()
      try:
          c.execute('SELECT value FROM data WHERE item = ?', (item, ))
          row = c.fetchone()
          if row:
              result = row[0]
          else:
              result = None
      except Exception:
          logging.exception('select failed: %s', item)
      finally:
          c.close()
      #logging.debug('sqlite got %s: %s', item, result)
      return result

  def set(self, item, value):
      insert = True
      if self.get(item) is not None:
          insert = False
      #logging.debug('sqlite insert %s: %s', item, value)
      c = self.conn.cursor()
      try:
          if insert:
              c.execute('INSERT INTO data VALUES (?, ?)',
                       (item, value))
          else:
              c.execute('UPDATE data SET item=?, value=? WHERE item = ?',
                        (item, value, item))

          self.conn.commit()
      except Exception:
          logging.exception('select failed: %s', item)
      finally:
          c.close()


  #def delete(self, item):
  #    #logging.debug('sqlite deleting %s', item)
  #    c = self.conn.cursor()
  #    try:
  #        c.execute('DELETE FROM data WHERE item = ?', (item, ))
  #        self.conn.commit()
  #    except Exception:
  #        logging.exception('delete failed: %s', item)
  #    finally:
  #        c.close()

  #def clear(self):
  #    if self.prefix not in self.__class__._conn:
  #        return
  #    self.conn.close()
  #    if FLAGS.datastore_path != ':memory:':
  #        os.unlink(os.path.join(FLAGS.datastore_path, '%s.sqlite' % self.prefix))
  #    del self.__class__._conn[self.prefix]

  #def clear_all(self):
  #    for k, conn in self.__class__._conn.iteritems():
  #        conn.close()
  #        if FLAGS.datastore_path != ':memory:':
  #            os.unlink(os.path.join(FLAGS.datastore_path,
  #                                   '%s.sqlite' % self.prefix))
  #    self.__class__._conn = {}


  #def set_add(self, item, value):
  #    group = self[item]
  #    if not group:
  #        group = []
  #    group.append(value)
  #    self[item] = group

  #def set_is_member(self, item, value):
  #    group = self[item]
  #    if not group:
  #        return False
  #    return value in group

  #def set_remove(self, item, value):
  #    group = self[item]
  #    if not group:
  #        group = []
  #    group.remove(value)
  #    self[item] = group

  #def set_fetch(self, item):
  #    # TODO(termie): I don't really know what set_fetch is supposed to do
  #    group = self[item]
  #    if not group:
  #        group = []
  #    return iter(group)


