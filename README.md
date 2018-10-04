# ScriptDog

ScriptDog stands for "**Script**ed **D**ial**og**ue". When writing scripted agents, like a chatbot, state is very important yet hard to keep track of. ScriptDog aims to abstract away any state handling and allows the developer to focus exclusively on the script the bot will follow.

## install
ScriptDog is a python package and so it is installed with pip.
```
pip3 install git+https://github.com/BYU-PCCL/scriptdog.git
```

It is meant to lightweight, so we extracted all complier logic into another repo located here: https://github.com/BYU-PCCL/scriptdog-compiler/. For development, it is recommended to also install the compiler.
```
pip3 install git+https://github.com/BYU-PCCL/scriptdog-compiler.git
```

However, they are kept seperate so that when you are deploying your chatbot, only `scriptdog` is needed to run your compiled scripts.

## use
The script syntax emulates python, but diverges where appropriate. There are a couple key concepts that are at the heart of ScriptDog.

#### stack-based
ScriptDog is stack-based. Meaning that if you have a function call, then after the function has executed the script will return to where it was and continue from there.

#### functions
Functions in ScriptDog are pretty much what you would expect them to be. The main function is called `start`. There has to be a `start` function in the script, otherwise it won't know where to begin from. It is considered best practice to make `start` a loop by adding a call to `start` at the end of the function. No worries though, due to tail-call optimization this will not create an infinite stack that will break your system.

#### patterns
Patterns can be thought of as a set of regex expressions that can be matched by an input. These are surrounded by brackets are are typically used right after an expect. They do overlap a little with functions in that they are not just patterns to be matched, but could also call another function as well. When the pattern makes another call internally, they are considered unsafe.

#### expect
The program will continually run until it hits an `expect` key word. The `expect` keyword is waiting for an input to continue.

## program samples
The recommended way to use ScriptDog can be seen in the samples folder. The raw scripts are the .dog files. The compiled scripts are the .pkl files. And the python file allows you to run your compiled scripts.

## cite us
If you use ScriptDog in any research endeavors, please cite us!

```
@misc{scriptdog2018,
  author = {David Wingate and Tyler Etchart},
  title = {ScriptDog},
  year = {2018},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/BYU-PCCL/scriptdog/}},
}
```
