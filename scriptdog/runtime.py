import sys
import subprocess
import string
import re
import random  # only needed for opt

from scriptdog.objs import (NamedStateOp, SetOp, ClearOp, ExpectOp, OptOp,
                            IfOp, ReturnOp, RegexvOp, AssgnOp, IdrefOp,
                            VarrefOp, ElseOp)

# =============================================================================


def NamedStateOp_exec(self, sd_prog, stack_obj):
    new_state_name = self.name

    # actual parameters
    actual_params_exprs = self.arg_list
    actual_params = []
    for param_ind in range(len(actual_params_exprs)):
        actual_params.append(
            param_eval(actual_params_exprs[param_ind],
                       stack_obj['scope_stack'], stack_obj['global_vars']))

    # is it an externally bound function?
    if new_state_name in sd_prog.external_state_functions:
        func = sd_prog.external_state_functions[new_state_name]
        return func(sd_prog, stack_obj, actual_params)

    else:
        # bind arguments
        # formal parameters
        formal_params = sd_prog.states[new_state_name].param_list
        new_scope = {}
        if len(formal_params) != len(actual_params):
            error('parameter mismatch!')
        for param_ind in range(len(formal_params)):
            new_scope[formal_params[param_ind]] = actual_params[param_ind]

        # as a small optimization, if the new_state_name is
        # the same as the current state name, we don't push
        # onto the stack.  tail call optimization, i guess.

        stack_obj['program_stack'].append((new_state_name, -1))
        stack_obj['scope_stack'].append(new_scope)


def SetOp_exec(self, sd_prog, stack_obj):

    lhs = self.arg_list[0]
    if len(self.arg_list) == 1:
        stack_obj['global_vars'][lhs] = True

    elif len(self.arg_list) == 2:
        rhs = param_eval(self.arg_list[1], stack_obj['scope_stack'],
                         stack_obj['global_vars'])
        # XXX HACKISH STRING
        if rhs[0] == '"' and rhs[-1] == '"':
            rhs = rhs[1:-1]
        stack_obj['global_vars'][lhs] = rhs


def ClearOp_exec(self, sd_prog, stack_obj):
    stack_obj['global_vars'].pop(self.id, None)


def ExpectOp_exec(self, sd_prog, stack_obj, cur_ut):

    retval = named_trans_match(sd_prog, cur_ut, self.named_trans,
                               stack_obj['scope_stack'],
                               stack_obj['global_vars'])

    if retval == False:
        # nothing matched.  test global utterances
        retval = global_trans_match(sd_prog, cur_ut, stack_obj['scope_stack'],
                                    stack_obj['global_vars'])
        if retval == False:
            # XXX REALLY nothing matched.  just continue.  log this?
            warn("nothing matched expect op!")
            return

    # ok! something matched.  the return value from named_trans_match can be unpacked like this:
    new_stack_stuff, _matched, _remaining = retval
    new_stack_stuff.reverse()
    for ss in new_stack_stuff:
        stack_obj['program_stack'].append((ss[0], ss[1]))
        stack_obj['scope_stack'].append(ss[2])


def OptOp_exec(self, sd_prog, stack_obj):

    # pick the new state
    weights = []
    for op_ref in self.op_set:
        weights.append(op_ref[1])

    # this isn't available until python 3.6.  Argh.
    # op_ind = random.choices( range(len(weights)), weights=weights )

    # i don't want to introduce a numpy dependency, so I'm just coding this up
    sum = 0.0
    for i in weights:
        sum += i
    val = random.random()
    cumsum = 0.0
    for op_ind in range(len(weights)):
        cumsum += (weights[op_ind] / sum)
        if val < cumsum:
            break

    op_ref = self.op_set[op_ind]

    stack_obj['program_stack'].append((op_ref[0], -1))
    stack_obj['scope_stack'].append({})


def IfOp_exec(self, sd_prog, stack_obj):

    # a "test" is an expression and a consequent state.  we implement "else" statements as a test that always succeeds
    for test in self.test_seq:
        varref_id, new_state_name = test
        passed = False
        if varref_id == None:  # an else statement
            passed = True
        else:
            retval = param_eval(varref_id, stack_obj['scope_stack'],
                                stack_obj['global_vars'])
            if retval:
                passed = True
        if passed:
            stack_obj['program_stack'].append((new_state_name, -1))
            stack_obj['scope_stack'].append({})
            break


def ReturnOp_exec(self, sd_prog, stack_obj):
    while True:
        next_state_name, next_op_ind = stack_obj['program_stack'].pop()
        stack_obj['scope_stack'].pop()
        if sd_prog.states[
                next_state_name].is_implicit:  # is it an implicitly created state?
            continue
        else:
            break


# ==================================================================================


def bind_runtime():
    NamedStateOp.exec = NamedStateOp_exec
    SetOp.exec = SetOp_exec
    ClearOp.exec = ClearOp_exec
    ExpectOp.exec = ExpectOp_exec
    OptOp.exec = OptOp_exec
    IfOp.exec = IfOp_exec
    ReturnOp.exec = ReturnOp_exec


# ==================================================================================

# XXX should this be part of the compiler?

# advantage: if we can make all patterns part of the compiled program,
# then we can use "re.compile" on them.  this would be faster, especially if we're repeatedly testing global patterns.
#
# disadvantage: if we do it at runtime, there is the possibility of dynamic matching.


def process_pattern(pattern):
    # these allows the user to write "i (just)? love you", instead of "i ?(just)? ?love you"
    pattern = re.sub(r" \(([a-z |]*?)\)\?", r" ?(\g<1>)?", pattern)
    pattern = pattern.replace(r")? ", r")? ?")

    # remove leading and trailing whitespace
    pattern = pattern.strip()

    return pattern


def processed_match(regex_str, ut):
    # print( "trying to match [%s] against [%s]" % ( ut, regex_str ) )
    processed_regex_str = process_pattern(regex_str)
    match = re.match(processed_regex_str, ut)
    return match


# ==================================================================================
# ==================================================================================
# ==================================================================================


def error(errstr):
    print(errstr, file=sys.stderr)
    print(errstr, file=sys.stdout)
    raise Exception(errstr)


def warn(errstr):
    #    print( errstr, file=sys.stderr )
    #    print( errstr, file=sys.stdout )
    pass


# =========================================
# =========================================
# =========================================

#
# We need to test an utterance against a possible transition.
#
# to match a transition, we can match any of the possible utterances inside of it.
#
# ut is the utterance - what the user said
# trans_name is the name of the transition we're testing.
#
# inside the transition is a list of UtteranceOp's
#
# these can consist of simple things (like a string match), or more
#   complex things (such as a reference to another named transition)
#
# we basically do a depth-first traversal of possible utterance matches.
# we transition to the state associated with the first match
#
# we accumulate several things while this is happening.  because
# utterances can have associated state transitions, and because they
# can be nested in arbitrary ways, the end result of this will be a
# fragment of states and scopes to be executed.
#
# this will then be placed at the head of the current program stack,
# and execution will commence.
#
# NOTE: global utterances are only tested once, at the outermost level (ie, when processing an expect op)
#


def named_trans_match(p, ut, trans_name, scope_stack, global_vars):

    #    print( "  testing [%s] against [%s]" % ( ut, trans_name ) )

    # check for externally bound transition functions
    if trans_name in p.external_utterance_matchers:
        return p.external_utterance_matchers[trans_name](
            p, ut, trans_name, scope_stack, global_vars)

    if not trans_name in p.transitions:
        error('attempt to reference unknown composite utterance ' + trans_name)

    trans = p.transitions[trans_name]

    for e_ind in range(len(trans.ut_seq)):
        retval = ut_match(p, ut, trans.ut_seq[e_ind], scope_stack, global_vars)
        if retval != False:
            #            stack_stuff, matched_ut, remaining_ut = retval
            #            print( retval )
            #            print( "  [%s] matched [%s] trans_name=[%s]!" % ( ut, matched_ut, trans_name ) )
            return retval

    # XXX nothing matched.
#    print( "  [%s] didn't match [%s]" % ( ut, trans_name ) )
    return False


# =========================================


def global_trans_match(p, ut, scope_stack, global_vars):

    for trans_name in p.transitions:
        if not p.transitions[trans_name].is_global:
            continue
#        print( "checking [%s] against global [%s]" % ( ut, trans_name ) )
        retval = named_trans_match(p, ut, trans_name, scope_stack, global_vars)
        if retval != False:
            #            print( "  matched!")
            return retval

    return False


#
# =========================================
#


def ut_match(p, ut, ut_op, scope_stack, global_vars):
    # ut is the utterance - what the user said
    # ut_op is the utteranceOp - a candidate match

    #
    #     <expect> {
    # idref        [name]
    # assgn        [X=NAME] -> <say "pleased to meet you {X}">
    # regexv       ["never mind"] -> <say "That's ok.">
    # composite    [YES? "my name is"? X=NAME] -> <say "thanks {X}">
    # else         [else] -> <say "I didn't quite catch that.  What was it again?">
    #     }

    stack_stuff = []
    scope = {}
    matched_ut = ""
    remaining_ut = ut

    # in order for an utterance to match, all of the individual ops have to match
    op_list = ut_op.ut_op_list
    for op in op_list:
        if type(op) == RegexvOp:
            #            print( "  testing [%s] against [%s]" % ( remaining_ut, op.regex_str ) )
            #            match = re.match( op.regex_str, remaining_ut )
            match = processed_match(op.regex_str, remaining_ut)
            if match == None:
                if not op.optional:
                    return False
                else:
                    continue
            # consume the match
            matched_ut += remaining_ut[match.start():match.end()]
            remaining_ut = remaining_ut[match.end():].lstrip()
#            print( "  matched -> [%s], [%s]" % ( matched_ut, remaining_ut ) )

        elif type(op) == AssgnOp:
            retval = named_trans_match(p, remaining_ut, op.rhs, scope_stack,
                                       global_vars)
            if retval == False:
                if not op.optional:
                    return False
                else:
                    continue

            new_stack_stuff, matched_ut, remaining_ut = retval
            scope[op.lhs] = matched_ut
            if new_stack_stuff != []:
                stack_stuff += new_stack_stuff

        elif type(op) == IdrefOp:
            retval = named_trans_match(p, remaining_ut, op.id, scope_stack,
                                       global_vars)
            if retval == False:
                if not op.optional:
                    return False
                else:
                    continue
            new_stack_stuff, matched_ut, remaining_ut = retval
            if new_stack_stuff != []:
                stack_stuff += new_stack_stuff

        elif type(op) == VarrefOp:
            retval = param_eval(op.id, scope_stack, global_vars)
            if retval == None or retval != True:
                if not op.optional:
                    return False
                else:
                    continue

        elif type(op) == ElseOp:
            matched_ut = ut
            remaining_ut = ""

    # ok!  if we've made it this far, all of the ops succeeded.  that means we have a match.
    #
    # take the associated state transition.
    #

    next_state_name = ut_op.next_state_name
    if next_state_name != None:
        stack_stuff += [[next_state_name, -1, scope]]

    return (stack_stuff, matched_ut, remaining_ut)


#
# =========================================
#
# parameters look like '{X}'
#


def key_lookup(key, scope_stack, global_vars):

    # start with the most recent scope
    for scope_ind in range(len(scope_stack) - 1, 0, -1):
        if key in scope_stack[scope_ind]:
            return scope_stack[scope_ind][key]

    if key in global_vars:
        return global_vars[key]

    error('unbound variable ' + key)


#
# =========================================
#


def param_eval(param, scope_stack, global_vars):

    # handle variable references like {X}
    if param[0] == '{':
        return key_lookup(param[1:-1], scope_stack, global_vars)

    # as a special case, we also interpolate parameters into strings <say "Hi {X}, I am {Y}">
    pat = r"(\{[a-zA-Z0-9_]+\})"
    matches = re.split(pat, param)
    new_str = []
    for m in matches:
        if m[0] == '{':
            new_str.append(key_lookup(m[1:-1], scope_stack, global_vars))
        else:
            new_str.append(m)

    return "".join(new_str)


#
# ==================================================================================
# ==================================================================================
# ==================================================================================
#
# a non-recursive execution model.
#
# this is necessary so that we can pause, serialize, and resume execution
#


def initial_stack():
    # the stack_obj always represents the location of the most
    # recently executed instruction.  conventionally, we use an
    # operation index of -1 to represent the fact that we've just
    # entered a new function -- so when we advance, it will be
    # pointing at instruction #0 in the function.

    # NOTE: we explicitly do not use any sort of python objects as
    # part of the state representation.  this is so that program state
    # can be easily JSON serializable.

    stack_obj = {
        "program_stack": [('start', -1)],
        "scope_stack": [{}],
        "global_vars": {}
    }
    return stack_obj


def copy_stack_obj(orig_stack_obj):
    # XXX this only does shallow copies.  which should be fine, i think.
    new_stack_obj = {}
    for key in orig_stack_obj.keys():
        new_stack_obj[key] = orig_stack_obj[key].copy()
    return new_stack_obj


def breakout_stack(sd_prog, stack_obj):
    program_stack = stack_obj['program_stack'][-1]
    cur_state_name, cur_op_ind = program_stack
    cur_state = sd_prog.states[cur_state_name]
    cur_op_seq = cur_state.op_seq
    return cur_state_name, cur_state, cur_op_ind, cur_op_seq


def advance_instruction_pointer(sd_prog, stack_obj):
    #
    # figure out the next instruction to execute
    #
    # note: mutates stack_obj in place
    #

    if len(stack_obj['program_stack']) == 0:
        # this program is all done! loop back to the start state, but keep global variables
        new_stack = initial_stack()
        stack_obj['program_stack'] = new_stack['program_stack']
        stack_obj['scope_stack'] = new_stack['scope_stack']

    while True:
        cur_state_name, cur_state, cur_op_ind, cur_op_seq = breakout_stack(
            sd_prog, stack_obj)

        # advance the op pointer
        cur_op_ind += 1

        if cur_op_ind >= len(cur_op_seq):
            # we've run off the end of the current state sequence, so
            # we need to return to the previous calling context.
            stack_obj['program_stack'].pop()
            stack_obj['scope_stack'].pop()
            continue
        else:
            # make sure the top of the stack is pointing to the instruction we're about to execute
            tmp = stack_obj['program_stack'].pop()
            stack_obj['program_stack'].append((tmp[0], cur_op_ind))
            break

    return cur_state_name, cur_state, cur_op_ind, cur_op_seq


def run_program_until_expect(sd_prog, orig_stack_obj, cur_ut):

    # we'll mutate this in place.  but there will be times we want to
    # rewind, so we don't want to clobber the original object
    stack_obj = copy_stack_obj(orig_stack_obj)

    #    print( "----------------------" )
    #    print( stack_obj )

    # the first time we run the program, we start in the start state,
    # not in the middle of an expect statement.
    if cur_ut != None:
        # now that we have an utterance, complete the execution of the most recent expect statement
        cur_state_name, cur_state, cur_op_ind, cur_op_seq = breakout_stack(
            sd_prog, stack_obj)
        cur_op = cur_op_seq[cur_op_ind]
        if type(cur_op) == ExpectOp:
            cur_op.exec(sd_prog, stack_obj, cur_ut)

    # now execute states until we hit an expectop
    while True:

        # print( "----------------------" )
        # print( stack_obj )

        cur_state_name, cur_state, cur_op_ind, cur_op_seq = advance_instruction_pointer(
            sd_prog, stack_obj)
        cur_op = cur_op_seq[cur_op_ind]

        if type(cur_op) == ExpectOp:
            # NOTE that this leaves the instruction pointer pointing
            # at an instruction that hasn't yet been executed!
            break
        else:
            op_result = cur_op.exec(sd_prog, stack_obj)
            if op_result is None:
                continue
            op_out, var_name = op_result
            if var_name:
                stack_obj["global_vars"][var_name] = op_out

    return stack_obj
