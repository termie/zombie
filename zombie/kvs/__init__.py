import gflags

from zombie import util


FLAGS = gflags.FLAGS
gflags.DEFINE_string('kvs_backend', 'zombie.kvs.redis.Store',
                     'backend to use for the kvs')
gflags.DEFINE_string('kvs_prefix', '',
                     'prefix to use for all keys in the kvs')

Store = util.LazyPluggable('kvs_backend')
