---
layout: post
title: "Practical Linux debugging using eBPF/BCC"
---

(e)BPF has come a long way in the last few years. As of 4.14, we now support
far more than our traditional (and namesake) packet filtering support -- the
ability to connect to arbitrary kprobes (added in 4.1), uprobes and tracepoints
(added in 4.7) have turned BPF from a specialised tool for network flows and
analysis to a generic tool to introspect almost any aspect of kernel or
userspace.

# Why use BPF over perf?

Before one makes any espousal of eBPF, one has to naturally compare it to its
predecessors. One of the most well-featured and well known is `perf`, a very
mature set of userspace tools that consume 
instrumentation and 
