---
layout: post
title: "Creating D and Z state processes on demand"
---

At [work](https://meta.com) several years ago I received what at the time I
thought was a pretty niche request. A team in the containers space was testing
container teardown, and wanted to make sure that their software was robust to D
state processes. I gave them some ideas, they implemented it, and that was
that. Fast forward to today, and I think I must have seen this request at least
four or five time in my time at the company, which suggests that while this may
still be a niche request, there's clearly a noticeable void in readily
accessible knowledge on the subject. Hopefully this article can improve that
somewhat :-)

# D and Z states

The D (uninterruptible sleep) state is a process state where a process is
sleeping and cannot be interrupted or killed directly by signals<sup>* see
note</sup>. This can become a problem for things like init systems or
containerisation platforms where the unwavering persistence of such processes
must be planned for and have strategies in place to not block forward progress.

<small><sup>*</sup> This is true in the majority of cases, but we do also have
`TASK_KILLABLE` where fatal signals (i.e. signals with terminal state and no
userspace signal handler) can still terminate the application in this
state.</small>

One example of where this is used is in DMA transfers and the like. DMA allows
hardware subsystems to access the main system memory for reading/writing
independently of the CPU, which is essential for efficient handling of large
volumes of data. Programs generally must not be interrupted in the midst of
such operations because DMA transfers are not typically designed to accommodate
or recover from partial or interrupted reads or writes.

A similar case is handling Z (zombie) state processes, which are formed when a
child process terminates but its parent process doesn't reap the child's exit
status, leaving the child's record dangling in the process table.

These states can become a problem for things like init systems or
containerisation platforms where the unwavering persistence of such processes
must be planned for and have strategies in place to not block forward progress.
