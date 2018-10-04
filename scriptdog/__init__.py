name = "scriptdog"

import string
import re
import pickle

import scriptdog.runtime as sdr

#
# --------------------------------------
# decorators
#


def state_op(function):
    def wrapper(sd_prog, stack_obj, arg_list):
        function(*arg_list)

    return wrapper


def bind_op(function):
    def wrapper(sd_prog, stack_obj, arg_list):
        if not arg_list:
            raise ValueError(
                "First param of function {} must be the variable to bind it to.".
                format(function.__name__))
        elif len(arg_list) == 1:
            return function(), arg_list[0]
        else:
            return function(*arg_list[1:]), arg_list[0]

    return wrapper


#
# --------------------------------------
# main scriptdog class
#


class ScriptDog:
    def __init__(self):
        self.contractions = {
            "can not": "cant",
            "did not": "didnt",
            "was not": "wasnt",
            "are not": "arent",
            "do not": "dont",
            "what is": "whats",
            "how is": "hows",
            "that is": "thats",
            "you are": "your",
            "youre": "your",
            "i am": "im",
            "he is": "hes",
            "she is": "shes",
            "we are": "were",
            "they are": "theyre",
        }

    # TODO: THIS FEELS LIKE IT DOESN'T BELONG HERE
    def process_statement(self, statement):
        # lowercase
        statement = statement.lower()

        # remove leading and trailing whitespace
        statement = statement.strip()

        # strip punctuation
        translator = str.maketrans('', '', string.punctuation)
        statement = statement.translate(translator)

        # remove the word "alexa"
        statement = statement.replace("alexa", "")

        # XXX maybe remove words like "um" "uh", etc?
        # XXX maybe remove doubled words?

        # contract words
        for key in self.contractions.keys():
            statement = statement.replace(key, self.contractions[key])

        # compress whitespace
        statement = re.sub(" +", " ", statement)

        return statement

    def load_program(self, program_filename):
        if not program_filename.endswith(".pkl"):
            print("programs are .pkl files generated using the compile script")
        self.sd_prog = pickle.load(open(program_filename, "rb"))
        sdr.bind_runtime()

    def init_stack(self):
        self.stack_obj = sdr.initial_stack()

    def load_stack(self, stack_obj):
        self.stack_obj = stack_obj

    def bind_function(self, function_keyword, function):
        self.sd_prog.bind_state(function_keyword, function)

    def run_repl(self):
        import readline
        while True:
            cur_ut = input('> ')
            cur_ut = self.process_statement(cur_ut)
            self.stack_obj = sdr.run_program_until_expect(
                self.sd_prog, self.stack_obj, cur_ut)

    def step(self, current_utterance):
        cur_ut = self.process_statement(current_utterance)
        self.stack_obj = sdr.run_program_until_expect(self.sd_prog,
                                                      self.stack_obj, cur_ut)
