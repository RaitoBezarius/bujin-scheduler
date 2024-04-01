# `bujin-scheduler` 🥷⛩️

`bujin-scheduler` is a user service daemon in charge of scheduling your TaskWarrior backlog on your local computer to a CalDAV calendar of your choice.

## Theory of operations

This is an opinionated tool for my own needs, feel free to take it apart and adjust it for yours.

I have too many things to do and over so many platforms, to fill the puzzle, I am often in need of something that can understand:

(a) my fatigue level based on what I do
(b) reprioritization based on realtime (new) emergencies
(c) how to avoid my own burnout

Most todo lists does not have a concept of well-being, they are ultimately
focused on "get things done", which is great when you have natural protection
against burnout from your own body.

I, unfortunately, don't.

## Design

Most of the time, TaskWarrior is used as the long-term storage for everything I need to do:

- I log everything there
- If I need an automation, I just built a synchronizer

In addition, TaskWarrior often does not contain a deadline concept (sometimes, do, sometimes don't).

Whereas my calendar contains my manually input tasks and represents a
short-term horizon of what are the tasks I need to deal with on a daily basis.

This software is about moving parts of the long term storage to the short term
horizon in a clever way, taking into account the previous constraints.

## Alternatives

I tried https://github.com/bergercookie/syncall before and it seems very nice,
unfortunately, I am a NixOS developer and I need software to run on NixOS.

I tried hard but the latest release had a bunch of issues with imports (or my
mispackaging), so I gave up and decided that rewriting mine will be faster.

My scheduling component is anyway isolated so could be reused with syncall
directly without the rest of my opinionated stuff.
