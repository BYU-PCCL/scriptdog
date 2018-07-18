'''A collection of objects that are used to describe the AST of a scriptdog program.

Note that there is no implementation / execution logic here.  that is
provided by a runtime interpreter.  Consequently, this module has no
external dependencies.

'''

#
# --------------------------------------
# these are the fundamental operations supported by our language
#


class StateOp():
    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def exec(self, sd_prog, stack_obj):
        print("ERROR NOT IMPLEMENTED")
        pass


class NamedStateOp(StateOp):
    '''
    transition to a new state

    <say "pleased to meet you, {X}">
'''

    def __init__(self, name, arg_list, weight=1.0):
        self.name = name
        self.arg_list = arg_list
        self.weight = weight


class SetOp(StateOp):
    '''
    set a global variable

    <!set know_name>
    <!set name {X}>
    <!set {aux_props {X}}>  # XXX not yet supported
'''

    def __init__(self, arg_list, weight=1.0):
        self.arg_list = arg_list
        self.weight = weight

    def __str__(self):
        return str(self.arg_list)

    def __repr__(self):
        return str(self.arg_list)


class ClearOp(StateOp):
    '''
    clears a global variable
'''

    def __init__(self, id, weight=1.0):
        self.id = id
        self.weight = weight

    def __str__(self):
        return str(self.id)

    def __repr__(self):
        return str(self.id)


class ExpectOp(StateOp):
    def __init__(self, named_trans, weight=1.0):
        self.named_trans = named_trans
        self.weight = weight

    def __str__(self):
        return str(self.named_trans)

    def __repr__(self):
        return str(self.named_trans)


class OptOp(StateOp):
    '''
    implements the "option" directive
    randomly transitions to one sub-state, with probability proportional to the listed weights.
    the weight is optional, and defaults to 1.0

    <opt> {
      1.0 <say "one">
      2.0 <say "two">
      <say "three">
    }
'''

    def __init__(self, op_set, weight=1.0):

        # this is a list of tuples.  each tuple is of the form (state_name, weight)
        self.op_set = op_set
        self.weight = weight

    def __str__(self):
        return str(self.op_set)

    def __repr__(self):
        return str(self.op_set)


class IfOp(StateOp):
    '''
    an ifop encapsulates both the primary <if > as well as all of the <elseif > and <else> statements.

    these are listed as a "test sequence"

'''

    def __init__(self, test_seq, weight=1.0):
        self.test_seq = test_seq
        self.weight = weight

    def __str__(self):
        return str(self.test_seq)

    def __repr__(self):
        return str(self.test_seq)


class ReturnOp(StateOp):
    '''
    implements a form of a return statement

    we bail early by just popping the stack to make this
    work like you would expect, we pop the stack until we
    hit the most recent named state.  this will "correctly"
    handle implicitly created functions that serve as code
    blocks.

    XXX this is super hackish.  But it generally
    does what you would expect.

'''

    def __init__(self, weight=1.0):
        self.weight = weight

    def __str__(self):
        return "return"

    def __repr__(self):
        return "return"


#
# --------------------------------------
# the things an utterance can do / be
#


class RegexvOp():
    def __init__(self, regex_str, optional):
        self.regex_str = regex_str
        self.optional = optional


class AssgnOp():
    def __init__(self, lhs, rhs, optional):
        self.lhs = lhs
        self.rhs = rhs
        self.optional = optional


class IdrefOp():
    def __init__(self, id, optional):
        self.id = id
        self.optional = optional


class VarrefOp():
    def __init__(self, id, optional):
        self.id = id
        self.optional = optional


class ElseOp():
    pass


# --------------------------------------


class UtteranceOp():
    def __init__(self, ut_op_list, next_state_name):
        self.ut_op_list = ut_op_list  # a list of things like IdrefOp, AssgnOp, etc.
        self.next_state_name = next_state_name  # where to go if the utterance succeeds


# --------------------------------------


class State():
    def __init__(self, name, op_seq, param_list, is_implicit=False):
        self.name = name
        self.op_seq = op_seq
        self.param_list = param_list
        self.is_implicit = is_implicit
        # implicitly created states are things that are factored out
        # of other expressions, and are treated specially (eg, for the
        # case of "return" statements)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


class Transition():
    def __init__(self, name, is_global, ut_seq):
        self.name = name
        self.ut_seq = ut_seq
        self.is_global = is_global

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


class Program():
    def __init__(self):
        self.states = {}
        self.transitions = {}

        self.external_state_functions = {}
        self.external_utterance_matchers = {}

        self.unique_state_name_counter = 0
        self.unique_trans_name_counter = 0

    def add_state(self, state_obj):
        if state_obj.name in self.states:
            print("WARNING: redefining state %s" % state_obj.name)
        self.states[state_obj.name] = state_obj

    def add_trans(self, trans_obj):
        if trans_obj.name in self.transitions:
            print("WARNING: redefining transition %s" % trans_obj.name)
        self.transitions[trans_obj.name] = trans_obj

    def bind_state(self, str_name, actual_func):
        self.external_state_functions[str_name] = actual_func

    def bind_utterance_matcher(self, str_name, actual_func):
        self.external_utterance_matchers[str_name] = actual_func

    def get_next_unique_state_name(self):
        state_name = "__state_" + str(self.unique_state_name_counter)
        self.unique_state_name_counter += 1
        return state_name

    def get_next_unique_trans_name(self):
        trans_name = "__trans_" + str(self.unique_trans_name_counter)
        self.unique_trans_name_counter += 1
        return trans_name
