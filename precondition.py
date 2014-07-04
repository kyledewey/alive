# Copyright 2014 The ALIVe authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from language import *

class BoolPred:
  def fixupTypes(self, types):
    for attr in dir(self):
      a = getattr(self, attr)
      if isinstance(a, (Type, Value, BoolPred)):
        a.fixupTypes(types)


################################
class TruePred(BoolPred):
  def __repr__(self):
    return 'true'

  def getTypeConstraints(self):
    return BoolVal(True)

  def toSMT(self, state):
    return BoolVal(True)


################################
class PredNot(BoolPred):
  def __init__(self, v):
    assert isinstance(v, BoolPred)
    self.v = v

  def __repr__(self):
    return '!%s' % self.v

  def getTypeConstraints(self):
    return self.v.getTypeConstraints()

  def toSMT(self, state):
    return Not(self.v.toSMT(state))


################################
class PredAnd(BoolPred):
  def __init__(self, v1, v2):
    assert isinstance(v1, BoolPred)
    assert isinstance(v2, BoolPred)
    self.v1 = v1
    self.v2 = v2

  def __repr__(self):
    return '(%s && %s)' % (self.v1, self.v2)

  def getTypeConstraints(self):
    return mk_and([self.v1.getTypeConstraints(),
                   self.v2.getTypeConstraints()])

  def toSMT(self, state):
    return And(self.v1.toSMT(state), self.v2.toSMT(state))


################################
class PredOr(BoolPred):
  def __init__(self, v1, v2):
    assert isinstance(v1, BoolPred)
    assert isinstance(v2, BoolPred)
    self.v1 = v1
    self.v2 = v2

  def __repr__(self):
    return '(%s || %s)' % (self.v1, self.v2)

  def getTypeConstraints(self):
    return mk_and([self.v1.getTypeConstraints(),
                   self.v2.getTypeConstraints()])

  def toSMT(self, state):
    return Or(self.v1.toSMT(state), self.v2.toSMT(state))


################################
class BinaryBoolPred(BoolPred):
  EQ, NE, Last = range(3)

  opnames = ['==', '!=']

  def __init__(self, op, v1, v2):
    assert 0 <= op < self.Last
    assert isinstance(v1, (Constant, Input))
    assert isinstance(v2, (Constant, Input))
    self.op = op
    self.v1 = v1
    self.v2 = v2

  def __repr__(self):
    return '(%s %s %s)' % (self.v1, self.opnames[self.op], self.v2)

  @staticmethod
  def getOpId(name):
    for i in range(BinaryBoolPred.Last):
      if BinaryBoolPred.opnames[i] == name:
        return i
    print 'Unknown boolean operator: ' + name
    exit(-1)

  def getTypeConstraints(self):
    return mk_and([self.v1.type == self.v2.type,
                   self.v1.getTypeConstraints(),
                   self.v2.getTypeConstraints()])

  def toSMT(self, state):
    v1 = self.v1.toSMT([], state, [])
    v2 = self.v2.toSMT([], state, [])
    return {
      self.EQ: lambda a,b: a == b,
      self.NE: lambda a,b: a != b,
    }[self.op](v1, v2)


################################
class LLVMBoolPred(BoolPred):
  isSignBit, NSWAdd, Last = range(3)

  opnames = {
    isSignBit: 'isSignBit',
    NSWAdd:    'WillNotOverflowSignedAdd',
  }
  opids = {v:k for k, v in opnames.items()}

  num_args = {
    isSignBit: 1,
    NSWAdd:    2,
  }

  def __init__(self, op, args):
    assert 0 <= op < self.Last
    for a in args:
      assert isinstance(a, (Constant, Input))
    self.op = op
    self.args = args
    if self.num_args[op] != len(args):
      print 'Wrong number of argument to %s (expected %d)' %\
        (self.opnames[op], self.num_args[op])
      exit(-1)

  def __repr__(self):
    args = [str(a) for a in self.args]
    return '%s(%s)' % (self.opnames[self.op], ', '.join(args))

  def getOpName(self):
    return self.opnames[self.op]

  @staticmethod
  def getOpId(name):
    try:
      return LLVMBoolPred.opids[name]
    except:
      print 'Unknown boolean predicate: ' + name
      exit(-1)

  def getTypeConstraints(self):
    return mk_and([v.getTypeConstraints() for v in self.args])

  def toSMT(self, state):
    args = [v.toSMT([], state, []) for v in self.args]
    return {
      self.isSignBit: lambda a: a == (1 << (a.sort().size()-1)),
      self.NSWAdd:    lambda a,b: SignExt(1,a)+SignExt(1,b) == SignExt(1, a+b)
    }[self.op](*args)