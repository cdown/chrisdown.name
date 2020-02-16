---
layout: post
title: "スワップの弁護：よくある誤解を解く"
lang: ja
translations:
    - lang: en
      url: /2018/01/02/in-defence-of-swap.html
---

[(This post is also available in English.)](/2018/01/02/in-defence-of-swap.html)

この記事は [In defence of swap: common misconceptions](https://chrisdown.name/2018/01/02/in-defence-of-swap.html) を [著者の Chris Down さんの許可](https://twitter.com/unixchris/status/1224285773660377089) を得て [Hiroaki Nakamura](https://github.com/hnakamur/) が日本語に翻訳したものです。 [原文のライセンス](https://github.com/cdown/chrisdown.name/blob/master/LICENSE) は [CC-BY 4.0](http://creativecommons.org/licenses/by/4.0/) であり、翻訳のライセンスも同じく CC-BY 4.0 とします。

---

長文を読みたくない方への要約：
<!--
tl;dr:
-->

1. スワップを持つことは正しく機能するシステムのかなり重要なポイントです。
   スワップが無ければ、まともなメモリ管理を実現することは難しくなります。
   <!-- Having swap is a reasonably important part of a well functioning system.
   Without it, sane memory management becomes harder to achieve. -->
2. スワップは一般的に緊急事態用のメモリを取得するためのものではなく、メモリの回収を平等に効率的に行うためのものです。
   実のところ「緊急事態用のメモリ」は一般的に盛大に悪影響を及ぼします。
   <!-- Swap is not generally about getting emergency memory, it's about making
   memory reclamation egalitarian and efficient. In fact, using it as
   "emergency memory" is generally actively harmful. -->
3. スワップを無効にすることはメモリ争奪の状況下においてディスク I/O が問題になることを回避してくれるわけではありません。
   単にディスク I/O スラッシングの対象を anonymous ページから file ページにシフトさせるだけです。
   これは効率が悪くなるだけでなく、回収元の選択対象となるページのプールが小さくなり、発端となっているメモリ争奪の状況をより悪化させることに寄与してしまいます。
   <!-- Disabling swap does not prevent disk I/O from becoming a problem under
   memory contention, it simply shifts the disk I/O thrashing from anonymous
   pages to file pages. Not only may this be less efficient, as we have a
   smaller pool of pages to select from for reclaim, but it may also contribute
   to getting into this high contention state in the first place. -->
4. 4.0 以前のカーネルのスワップ機構はたくさんの落とし穴がありました。
   そして、必要以上にやたらとページをスワップアウトしたがるせいでスワップについてネガティブな認識を多くの人が持つようになりました。
   4.0 以降のカーネルでは状況ははるかに良くなっています。
   <!-- The swapper on kernels before 4.0 has a lot of pitfalls, and has contributed
   to a lot of people's negative perceptions about swap due to its
   overeagerness to swap out pages. On kernels >4.0, the situation is
   significantly better. -->
5. SSD では anonymous ページをスワップアウトするのと file ページを回収するのはパフォーマンスとレイテンシの観点では実質的には同じです。
   より古い回転ディスクではスワップからの読み込みはランダムリードになるためより遅くなります。
   ですので vm.swappiness をより低い値に設定することが理にかなっています（vm.swappiness については後述）。
   <!-- On SSDs, swapping out anonymous pages and reclaiming file pages are
   essentially equivalent in terms of performance/latency. On older spinning
   disks, swap reads are slower due to random reads, so a lower `vm.swappiness`
   setting makes sense there (read on for more about `vm.swappiness`). -->
6. スワップを無効にすることは OOM が近いときにを病的な挙動を防いでくれるわけではありません。
   一方、スワップがあれば OOM の発動を引き延ばせる可能性があるのは事実です。
   スワップありあるいはなしでシステムグローバルの OOM キラーが実行されるか、また実行される時期が早いか遅いか、に関わらず結果は同じです。
   つまりあなたには挙動が予測できないシステムが残されることになります。
   スワップを持たないことでこれを回避することはできません。
   <!-- Disabling swap doesn't prevent pathological behaviour at near-OOM, although
   it's true that having swap may prolong it. Whether the system global OOM
   killer is invoked with or without swap, or was invoked sooner or later, the
   result is the same: you are left with a system in an unpredictable state.
   Having no swap doesn't avoid this. -->
7. cgroup v2 の memory.low などを使うことでメモリ逼迫の状況下でスワップの挙動を改善しスラッシングを防ぐことができます。
   <!-- You can achieve better swap behaviour under memory pressure and prevent
   thrashing using `memory.low` and friends in cgroup v2. -->

---

カーネルのメモリ管理と [cgroup v2](https://www.youtube.com/watch?v=ikZ8_mRotT4) を改善する仕事の一環として、私は多くのエンジニアとメモリ管理についての考え方、特にメモリ逼迫時のアプリケーションの挙動とメモリ管理のために内部で使われるオペレーティングシステムのヒューリティックについて、話し合ってきました。
<!--
As part of my work improving kernel memory management and [cgroup
v2](https://www.youtube.com/watch?v=ikZ8_mRotT4), I've been talking to a lot of
engineers about attitudes towards memory management, especially around
application behaviour under pressure and operating system heuristics used under
the hood for memory management.
-->

これらのディスカッションで繰り返されるトピックはスワップです。
スワップは激しい論争の的になり、長年 Linux に取り組んでいる人たちにですらほとんど理解されていないトピックです。
多くの人はスワップを無意味だと考えていたりあるいは盛大に悪影響を及ぼすと考えています。
しかしそれはメモリが十分でなくディスクがページングに必要な容量を提供するための必要悪だった時代の古い考え方です。
この発言は近年いまだにかなりの頻度であちこちで見られ、私は同僚、友人、業界の仲間たちとディスカッションし、過去に比べて格段に増えた物理メモリを持つモダンなコンピュータ上でもスワップが引き続き有用な概念であることを理解するのを助けてきました。
<!--
A repeated topic in these discussions has been swap. Swap is a hotly contested
and poorly understood topic, even by those who have been working with Linux for
many years. Many see it as useless or actively harmful: a relic of a time where
memory was scarce, and disks were a necessary evil to provide much-needed space
for paging. This is a statement that I still see being batted around with
relative frequency in recent years, and I've had many discussions with
colleagues, friends, and industry peers to help them understand why swap is
still a useful concept on modern computers with significantly more physical
memory available than in the past.
-->

スワップの目的については多くの誤解があります。多くの人はスワップを単に緊急事態の際に利用できる「遅い追加メモリ」として見ていて、通常の負荷の際にオペレーティングシステム全体として健全に稼働することに貢献できることを理解していません。
<!--
There's also a lot of misunderstanding about the purpose of swap -\- many people
just see it as a kind of "slow extra memory" for use in emergencies, but don't
understand how it can contribute during normal load to the healthy operation of
an operating system as a whole.
-->

私たちの多くは「[Linux はメモリをたくさん使いすぎる](https://www.linuxatemyram.com/)」、「[スワップは物理メモリの 2 倍のサイズにすべき](https://superuser.com/a/111510/98210)」などというよくある言い回しを聞いたことがあるでしょう。
これらを打ち消すのはささいなことですが、これらについてのディスカッションは近年微妙なニュアンスを持つようになってきており、「役に立たない」スワップの神話は単純なアナロジーで説明できる何かというよりヒューリスティックと神秘に根ざしたものになり、検証するためにメモリ管理についての理解以上の何かが必要となっています。
<!--
Many of us have heard most of the usual tropes about memory: "[Linux uses too
much memory](https://www.linuxatemyram.com/)", "[swap should be double your
physical memory size](https://superuser.com/a/111510/98210)", and the like.
While these are either trivial to dispel, or discussion around them has become
more nuanced in recent years, the myth of "useless" swap is much more grounded
in heuristics and arcana rather than something that can be explained by simple
analogy, and requires somewhat more understanding of memory management to
reason about.
-->

このポストは Linux システムを管理している人で、少なすぎるスワップやスワップなしで稼働させたり vm.swappiness を 0 に設定して稼働させることへの反論を聞くことに興味がある人を主に対象としています。
<!--
This post is mostly aimed at those who administrate Linux systems and are
interested in hearing the counterpoints to running with undersized/no swap or
running with `vm.swappiness` set to 0.
-->

## 背景 <!-- Background -->

Linux のメモリ管理内で動いている基本的な内部の仕組みの一部について共通の理解がなければ、通常のオペレーションにおいてスワップを持つこととページをスワップアウトすることがなぜ良いことであるかについて話すのは難しいです。
ですのでまず同じページに立つことを確実にしましょう。
<!--
It's hard to talk about why having swap and swapping out pages are good things
in normal operation without a shared understanding of some of the basic
underlying mechanisms at play in Linux memory management, so let's make sure
we're on the same page.
-->

### メモリの種別 <!-- Types of memory -->

Linux には多くの異なるメモリの種別があり、それぞれが固有の特性を持っています。
これらの微妙な差異を理解することがなぜスワップが重要であるかを理解するための鍵です。
<!--
There are many different types of memory in Linux, and each type has its own
properties. Understanding the nuances of these is key to understanding why swap
is important.
-->

例えば、あなたのコンピュータ上で動いている各プロセスに対してコードを保持する責任を負う [*ページ*（メモリの「*ブロック*」、たいていは 4KiB）](https://en.wikipedia.org/wiki/Page_(computer_memory))があります。
またプログラムによってアクセスされるファイルに関連したデータやメタデータをキャッシュすることに責任を負うページもあります。
これらは [ページキャッシュ](https://en.wikipedia.org/wiki/Page_cache) の一部であり、ここでは *file* メモリと呼ぶことにします。
<!--
For example, there are [*pages* ("blocks" of memory, typically
4k)](https://en.wikipedia.org/wiki/Page_(computer_memory)) responsible for
holding the code for each process being run on your computer. There are also
pages responsible for caching data and metadata related to files accessed by
those programs in order to speed up future access. These are part of the [page
cache](https://en.wikipedia.org/wiki/Page_cache), and I will refer to them as
*file* memory.
-->

また、コード内部でメモリ割り当てに責任を負うページもあります。
例えば、 `malloc` によって新しいメモリが割り当てられたときや `mmap` の `MAP_ANONYMOUS` フラグを使う時です。
これらは何かによる裏付けが無い（訳注：バッキングストアを持たない）ので "anonymous"  ページと呼ばれます。
ここでは *anon* メモリと呼ぶことにします。
<!--
There are also pages which are responsible for the memory allocations made
inside that code, for example, when new memory that has been allocated with
`malloc` is written to, or when using `mmap`'s `MAP_ANONYMOUS` flag. These are
"anonymous" pages -\- so called because they are not backed by anything -\- and I
will refer to them as *anon* memory.
-->

他のタイプのメモリもあります。共有メモリ、スラブメモリ、カーネルスタックのメモリ、バッファなどです。
ですが、 anonymous メモリと file メモリが最もよく知られており理解しやすいので、ここでの例ではそれらを使います。
が、ここでの例はこれらの他のタイプにも同様に当てはまります。
<!--
There are other types of memory too -\- shared memory, slab memory, kernel stack
memory, buffers, and the like -\- but anonymous memory and file memory are the
most well known and easy to understand ones, so I will use these in my
examples, although they apply equally to these types too.
-->

### 回収可能なメモリと回収不可能なメモリ <!-- Reclaimable/unreclaimable memory -->

メモリの特定の種別について考えるときの最も根本的な質問の 1 つはそのメモリが回収可能であるかそうでないかということです。
ここでは「回収」とはシステムがデータを失うことなく物理メモリからその種別のページをパージすることを意味します。
<!--
One of the most fundamental questions when thinking about a particular type of
memory is whether it is able to be reclaimed or not. "Reclaim" here means that
the system can, without losing data, purge pages of that type from physical
memory.
-->

あるページ種別に対しては、これはたいていはとても自明です。
例えば *クリーン* な（修正されていない）ページキャッシュメモリの場合は、パフォーマンスのためにディスク上の何かを単にキャッシュしているだけなので、何か特別な操作をする必要もなくページをドロップできます。
<!--
For some page types, this is typically fairly trivial. For example, in the case
of *clean* (unmodified) page cache memory, we're simply caching something that
we have on disk for performance, so we can drop the page without having to do
any special operations.
-->

あるページ種別に対しては、これは可能ですが、自明ではありません。
例えば *ダーティ* な（修正された）ページキャッシュメモリの場合は、修正内容をまだディスクに反映していないので単にページをドロップは出来ません。
そのため回収を拒否するか、まず変更内容をディスクに反映してからこのメモリをドロップする必要があります。
<!--
For some page types, this is possible, but not trivial. For example, in the
case of *dirty* (modified) page cache memory, we can't just drop the page,
because the disk doesn't have our modifications yet. As such we either need to
deny reclamation or first get our changes back to disk before we can drop this
memory.
-->

あるページ種別に対しては、これは不可能です。
例えば、上で説明した anonymous ページの場合は、メモリ内にのみ存在し、他にバッキングストアが無いので、メモリ内に維持し続けるしかありません。
<!--
For some page types, this is not possible. For example, in the case of the
anonymous pages mentioned previously, they only exist in memory and in no other
backing store, so they have to be kept there.
-->

## スワップの性質について <!-- On the nature of swap -->

Linux のスワップの目的についての説明を探すと、多くの人がスワップを緊急事態の際に利用できる物理 RAM の単なる拡張であるかのように話しているのを否応なく目にするでしょう。
例えば、以下は私が Google で "what is swap" で検索した検索結果の上位からランダムに選んだものです。
<!--
If you look for descriptions of the purpose of swap on Linux, you'll inevitably
find many people talking about it as if it is merely an extension of the
physical RAM for use in emergencies. For example, here is a random post I got
as one of the top results from typing "what is swap" in Google:
-->

<!--googleoff: snippet-->

> スワップは実質的に緊急メモリです。
> あなたが持っている RAM よりも多くの物理メモリをシステムが一時的に必要とするときのために取っておく領域です。
> スワップは遅くて非効率という意味で「悪」と考えられており、システムがスワップを定常的に使う必要があるのであれば、それは明らかに十分なメモリを持っていないということです。 […]
> あなたの要求を全て処理するのに十分な RAM があり、それを超えることが絶対起こらないと言えるなら、スワップスペースなしでシステムを稼働することは完全に安全と言えるでしょう。

<!--
> Swap is essentially emergency memory; a space set aside for times when your
> system temporarily needs more physical memory than you have available in RAM.
> It's considered "bad" in the sense that it's slow and inefficient, and if
> your system constantly needs to use swap then it obviously doesn't have
> enough memory. [...] If you have enough RAM to handle all of your needs, and
> don't expect to ever max it out, then you should be perfectly safe running
> without a swap space.
-->

<!--googleon: snippet-->

誤解のないように言うと、この記事の内容についてこのコメントの投稿者を責めるつもりは全くありません。
これは多くの Linux システム管理者で「常識」として受け入れられ、スワップについて話す際に彼らに聞くと誰かが答えるたぶんもっともありそうな答えの 1 つでしょう。
しかし、これは残念ながらスワップの目的と使い方、特にモダンなシステムでの、についての誤解でもあります。
<!--
To be clear, I don't blame the poster of this comment at all for the content of
their post -\- this is accepted as "common knowledge" by a lot of Linux
sysadmins and is probably one of the most likely things that you will hear from
one if you ask them to talk about swap. It is unfortunately also, however, a
misunderstanding of the purpose and use of swap, especially on modern systems.
-->

上記で、 anonymous ページの回収が「可能ではない」ことについて述べました。
anonymous ページはメモリからパージしたときにフォールバックするバッキングストアがないという性質のため、回収してしまうとそれらのページのデータを完全に失うことになるからです。
でもそれらのページに対してそれができるストアを作れるとしたらどうでしょう？
<!--
Above, I talked about reclamation for anonymous pages being "not possible", as
anonymous pages by their nature have no backing store to fall back to when
being purged from memory -\- as such, their reclamation would result in complete
data loss for those pages. What if we could create such a store for these
pages, though?
-->

実は、それこそがまさにスワップの目的なのです。
スワップはこれらの「回収不可能」に見えるページを必要に応じてストレージデバイスにページアウトすることを実現するためのストレージエリアです。
このことは anonymous ページがクリーンな file ページなど、より明らかに回収可能な種別のページと今や同程度に回収対象としてふさわしいと考えることができるようになったことを意味し、利用可能な物理メモリをより効率的に使用できるようになります。
<!--
Well, this is precisely what swap is for. Swap is a storage area for these
seemingly "unreclaimable" pages that allows us to page them out to a storage
device on demand. This means that they can now be considered as equally
eligible for reclaim as their more trivially reclaimable friends, like clean
file pages, allowing more efficient use of available physical memory.
-->

**スワップは主に回収の平等さのための機構であり、緊急事態の際の「追加のメモリ」ではないのです。スワップがあなたのアプリケーションを遅くする正体ではありません。全体的なメモリ争奪の状態に入ることがあなたのアプリケーションを遅くする正体なのです。**
<!--
**Swap is primarily a mechanism for equality of reclamation, not for emergency
"extra memory". Swap is not what makes your application slow -\- entering
overall memory contention is what makes your application slow.**
-->

ではこの「回収の平等さ」の元でどんな状況が anonymous ページの回収を合法的に選択するのでしょう？ 以下は抽象的ないくつかの珍しくないシナリオです。
<!--
So in what situations under this "equality of reclamation" scenario would we
legitimately choose to reclaim anonymous pages? Here are, abstractly, some not
uncommon scenarios:
-->

1. 初期化の間、長時間実行されるプログラムはたくさんのページを割り当てて利用するかもしれません。
   これらのページはシャットダウンやクリーンアップの一部として使われるかもしれませんが、プログラムが一旦（各アプリケーションに固有の意味で）「開始」すると不要です。
   これは初期化のために大きな依存を持つデーモンでは非常によくあることです。
   <!-- During initialisation, a long-running program may allocate and use many
   pages. These pages may also be used as part of shutdown/cleanup, but are not
   needed once the program is "started" (in an application-specific sense).
   This is fairly common for daemons which have significant dependencies to
   initialise. -->
2. プログラムの通常の稼働中、たまにしか使われないメモリを割り当てるかもしれません。
   これらのページに必要に応じてディスクからページインする [メジャーフォールト](https://en.wikipedia.org/wiki/Page_fault#Types) を要求し、代わりにより重要な他のことにメモリを使うほうがシステム全体のパフォーマンスにとってはより合理的かもしれません。
   <!-- During the program's normal operation, we may allocate memory which is only
   used rarely. It may make more sense for overall system performance to
   require a [major fault](https://en.wikipedia.org/wiki/Page_fault#Types) to
   page these in from disk on demand, instead using the memory for
   something else that's more important. -->

## スワップのあるなしで何が起こるかを調べる <!-- Examining what happens with/without swap -->

典型的な状況でスワップのあるなしでパフォーマンスがどうなるかを見てみましょう。
[cgroup v2 についての私の講演](https://www.youtube.com/watch?v=ikZ8_mRotT4) で「メモリ争奪」についてのメトリクスについて話しています。
<!--
Let's look at typical situations, and how they perform with and without swap
present. I talk about metrics around "memory contention" in my [talk on cgroup
v2](https://www.youtube.com/watch?v=ikZ8_mRotT4).
-->

### メモリ争奪がないか程度が低い時 <!-- Under no/low memory contention -->

- **スワップがある時:** プロセスのライフサイクルの小さな一部のみで使用される、めったに使われない anonymous メモリをスワップアウトの対象として選ぶことができ、そのメモリをキャッシュのヒット率を改善するのに使ったり、あるいは他の最適化をしたりできます。
  <!-- **With swap:** We can choose to swap out rarely-used anonymous memory that
  may only be used during a small part of the process lifecycle, allowing us to
  use this memory to improve cache hit rate, or do other optimisations. -->
- **スワップがない時:** めったに使われないメモリであってもメモリ内にロックされているのでスワップアウトすることはできません。
  これが直ちに問題とはならないかもしれませんが、あるワークロードによっては、古い anonymous ページがより重要な用途にその空間を使わせないことにより自明でないパフォーマンスの低下を引き起こすかもしれません。
  <!-- **Without swap:** We cannot swap out rarely-used anonymous memory, as it's
  locked in memory. While this may not immediately present as a problem, on
  some workloads this may represent a non-trivial drop in performance due to
  stale, anonymous pages taking space away from more important use. -->

### 中程度あるいは高度にメモリ争奪がある時 <!-- Under moderate/high memory contention -->

- **スワップがある時:** 全てのメモリ種別が同じ確率で回収されます。これはページの回収が成功する可能性がより高いことを意味します。
  つまり、回収後にすぐ再びフォールトバック（スラッシング）しないようなページを回収できる可能性が上がるということです。
  <!-- **With swap:** All memory types have an equal possibility of being reclaimed.
  This means we have more chance of being able to reclaim pages successfully -\-
  that is, we can reclaim pages that are not quickly faulted back in again
  (thrashing). -->
- **スワップがない時:** anonymous ページは行き先が無いのでメモリ内にロックされます。
  そもそも一部のメモリ種別しか回収可能でないので、長期間にわたるページの回収の成功確率はより低くなります。
  ページスラッシングのリスクはより高くなります。
  詳しくないユーザはこの状況でもディスク I/O が発生するより良いと考えるかもしれませんが、それは正しくありません。
  実際にはスワップのディスク I/O の代わりにホットなページキャッシュをドロップしたり今後すぐに必要となるコードセグメントをドロップすることに単に移行しているだけなのです。
  <!-- **Without swap:** Anonymous pages are locked into memory as they have nowhere
  to go. The chance of successful long-term page reclamation is lower, as we
  have only some types of memory eligible to be reclaimed at all. The risk of
  page thrashing is higher. The casual reader might think that this would still
  be better as it might avoid having to do disk I/O, but this isn't true -\- we
  simply transfer the disk I/O of swapping to dropping hot page caches and
  dropping code segments we need soon. -->

### メモリ使用が一時的にスパイクしている時 <!-- Under temporary spikes in memory usage -->

- **スワップがある時:** 一時的なスパイクに大してより回復力は高くなり、深刻なメモリ飢餓の場合のメモリスラッシングの開始から OOM キラーまでの期間を引き延ばせるかもしれません。
  メモリ逼迫の扇動者に対してより可視性が高まり、それらに対してより合理的に働きかけ、コントロールされた介入を実行できます。
  <!-- **With swap:** We're more resilient to temporary spikes, but in cases of
  severe memory starvation, the period from memory thrashing beginning to the
  OOM killer may be prolonged. We have more visibility into the instigators of
  memory pressure and can act on them more reasonably, and can perform a
  controlled intervention. -->
- **スワップがない時:** anonymous ページがメモリにロックされ回収不可能なため OOM キラーがより早く実行されます。
  メモリスラッシングがより起きやすくなり、スラッシングから OOM までの期間は短くなります。
  あなたのアプリケーション次第で、これは良いことも悪いこともあり得ます。
  例えば、キューベースのアプリケーションはスラッシングからキルに素早く移行することが望ましいかもしれません。
  と言っても、実際に有用になるにはそれでも遅すぎます。
  OOM キラーが実行されるのは深刻な飢餓の瞬間になってからでしかないからです。
  そのような振る舞いに対してこの方法に頼ることよりも最初にメモリ争奪が起きた時に機会を逃さずにプロセスをキルするほうが良いはずです。
  <!--**Without swap:** The OOM killer is triggered more quickly as anonymous pages
  are locked into memory and cannot be reclaimed. We're more likely to thrash
  on memory, but the time between thrashing and OOMing is reduced. Depending on
  your application, this may be better or worse. For example, a queue-based
  application may desire this quick transfer from thrashing to killing. That
  said, this is still too late to be really useful -\- the OOM killer is only
  invoked at moments of severe starvation, and relying on this method for such
  behaviour would be better replaced with more opportunistic killing of
  processes as memory contention is reached in the first place. -->

### オーケー、システムスワップが必要なことは分かったけど、個別のアプリケーションに対してどのように調整すれば良いでしょうか？ <!-- Ok, so I want system swap, but how can I tune it for individual applications? -->

まさかこの記事全体を通して私が cgroup v2 の話を差し込まずに終わるとは思って無いですよね？ ;-)
<!--
You didn't think you'd get through this entire post without me plugging cgroup
v2, did you? ;-)
-->

もちろん、一般的なヒューリスティックなアルゴリズムがいつも正しくあることは難しいです。
ですので、あなたがカーネルに助言を与えられることが重要です。
歴史的には実行可能な唯一のチューニングはシステムレベルで `vm.swappiness` を使うことだけでした。
これには 2 つの問題があります。
`vm.swappiness` はより大きなヒューリスティックなシステムの小さな一部に注入するだけなのと、
プロセス群のより小さなセットではなくシステム全体に対する設定であるので、理解するのが信じられないほど難しいです。
<!--
Obviously, it's hard for a generic heuristic algorithm to be right all the time,
so it's important for you to be able to give guidance to the kernel.
Historically the only tuning you could do was at the system level, using
`vm.swappiness`. This has two problems: `vm.swappiness` is incredibly hard to
reason about because it only feeds in as a small part of a larger heuristic
system, and it also is system-wide instead of being granular to a smaller set
of processes.
-->

`mlock` を使ってページをメモリ内にロックすることも出来ますが、これはプログラムコードを修正するか、 `LD_PRELOAD` で楽しく遊ぶか、実行時にデバッガで恐ろしいことをするかのいずれかが必要です。
さらに VM ベースの言語ではこれはあまりうまく動きません。
というのは、一般的にはアロケーションについてあなたが制御できないので結局 `mlockall` を使わざるを得なくなり、それでは実際に大切にしたいページに対して正確に制御できないからです。
<!--
You can also use `mlock` to lock pages into memory, but this requires either
modifying program code, fun with `LD_PRELOAD`, or doing horrible things with a
debugger at runtime. In VM-based languages this also doesn't work very well,
since you generally have no control over allocation and end up having to
`mlockall`, which has no precision towards the pages you actually care about.
-->

cgroup v2 は `memory.low` の形式で cgroup 単位の調整が可能で、これによりメモリ使用量がある閾値を下回ったら他のアプリケーションからメモリを回収することを優先するようカーネルに伝えることができます。
これによりカーネルが私たちのアプリケーションの部分をスワップアウトするのを防ぐだけでなく、メモリ争奪時に他のアプリケーションから回収することを優先するようにできます。
通常の状況下では、カーネルのスワップのロジックは一般的にはかなり良く、ページを機会に応じてスワップアウトするのを許可することは一般的にシステムのパフォーマンスを増大します。
大量のメモリ争奪下でのスワップのスラッシングは理想的ではないですが、それはスワップ機構の問題というよりも単にメモリ全体を使い切ったことによる特性です。
これらの状況では、メモリ逼迫の圧力が積みあがるときに致命的でないプロセスが自分をキルすることでフェールファーストすることがたいていは望ましいでしょう。
<!--
cgroup v2 has a tunable per-cgroup in the form of `memory.low`, which allows us
to tell the kernel to prefer other applications for reclaim below a certain
threshold of memory used. This allows us to not prevent the kernel from
swapping out parts of our application, but prefer to reclaim from other
applications under memory contention. Under normal conditions, the kernel's
swap logic is generally pretty good, and allowing it to swap out pages
opportunistically generally increases system performance. Swap thrash under
heavy memory contention is not ideal, but it's more a property of simply
running out of memory entirely than a problem with the swapper. In these
situations, you typically want to fail fast by self-killing non-critical
processes when memory pressure starts to build up.
-->

これには単に OOM キラーに頼るということはできません。
OOM キラーはシステムが深刻的に不健全になりしばらくそれが続く状態に *既に* 入った時に切迫した障害の状況になったときにしか実行されないからです。
あなたは OOM キラーについて一度でも考える前に、適切な機会にあなた自身で状況を処理する必要があります。
<!--
You can not simply rely on the OOM killer for this. The OOM killer is only
invoked in situations of dire failure when we've *already* entered a state
where the system is severely unhealthy and may well have been so for a while.
You need to opportunistically handle the situation yourself before ever
thinking about the OOM killer.
-->

しかし、従来の Linux のメモリカウンタを使ってメモリ逼迫が起こっているを判断することはやや難しいです。
メモリ消費量、ページスキャン、などある程度関係する何かはありますが、なんとか関係している程度でしかありません。
そしてこれらのメトリックだけから効率的なメモリ配置からメモリ争奪への切り替わり傾向が起きていることを判断するのは非常に難しいです。
Facebook では [Johannes](https://patchwork.kernel.org/project/LKML/list/?submitter=45) が先陣を切る私たちのグループがあり、メモリ逼迫をもっと容易に明らかにする新しいメトリクスの開発に取り組んでいますので、将来にはこれが役立つでしょう。
これについてもっと聞くことに興味があれば [cgroup v2 についての私の講演で検討中の 1 つのメトリックについて詳細に触れています](https://youtu.be/ikZ8_mRotT4?t=2145) 。
<!--
Determination of memory pressure is somewhat difficult using traditional Linux
memory counters, though. We have some things which seem somewhat related, but
are merely tangential -\- memory usage, page scans, etc -\- and from these
metrics alone it's very hard to tell an efficient memory configuration from one
that's trending towards memory contention. There is a group of us at Facebook,
spearheaded by
[Johannes](https://patchwork.kernel.org/project/LKML/list/?submitter=45),
working on developing new metrics that expose memory pressure more easily that
should help with this in future. If you're interested in hearing more about
this, [I go into detail about one metric being considered in my talk on cgroup
v2](https://youtu.be/ikZ8_mRotT4?t=2145).
-->

## チューニング <!-- Tuning -->

### ではスワップのサイズはどれぐらい必要なのでしょう？ <!-- How much swap do I need, then? -->

一般に、オプショナルなメモリ管理に必要なスワップスペースの最小の量は、アプリケーションによってめったに再びアクセスされないメモリにピン止めされる anonymous ページの数とそれらの anonymous ページを回収する回数に依存します。
後者は主にアクセス頻度の低い anonymous ページに道を譲るためにどのページがもうパージされなくなるかの問題です。
<!--
In general, the minimum amount of swap space required for optimal memory
management depends on the number of anonymous pages pinned into memory that are
rarely reaccessed by an application, and the value of reclaiming those
anonymous pages. The latter is mostly a question of which pages are no longer
purged to make way for these infrequently accessed anonymous pages.
-->

山ほどのディスクスペースと最近 (4.0+) のカーネルをお持ちでしたら、より大きなスワップは小さなスワップよりほぼ常に良いです。
より古いカーネルの `kswapd` 、これはスワップを管理する責任を負うカーネルプロセスの 1 つです、は歴史的にスワップをより多く持つほどメモリをアグレッシブにスワップアウトすることに非常に熱心すぎるものでした。
最近では、大きな容量のスワップスペースがある時のスワッピングの振る舞いは著しく改善されています。
カーネル 4.0+ を稼働していれば、モダンなカーネル上でより大きなスワップを持つことは熱心すぎるスワップに終わることはないはずです。
ですので、スペースに余裕があれば、数 GB のスワップサイズを持つことはモダンなカーネルでは有効な選択肢でしょう。
<!--
If you have a bunch of disk space and a recent (4.0+) kernel, more swap is
almost always better than less. In older kernels `kswapd`, one of the kernel
processes responsible for managing swap, was historically very overeager to
swap out memory aggressively the more swap you had. In recent times, swapping
behaviour when a large amount of swap space is available has been significantly
improved. If you're running kernel 4.0+, having a larger swap on a modern
kernel should not result in overzealous swapping. As such, if you have the
space, having a swap size of a few GB keeps your options open on modern
kernels.
-->

もしディスクスペースにもっと制約があるなら、回答はあなたが決めるトレードオフと環境の性質に大いに依存します。
理想的にはあなたのシステムを通常とピークの（メモリの）負荷の際に最適に稼働させるために十分なサイズのスワップを持つべきでしょう。
私がお勧めするのは 2-3GB かそれ以上のスワップを持ついくつかのテストシステムをセットアップし、ささまざまな（メモリの）負荷状況の元で 1 週間程度の連続稼働をして何が起こるかをモニタリングすることです。
その週の間深刻なメモリ飢餓が起きない限りはテストがあまり有用でなかったということになりますが、おそらくは数 MB 程度スワップが使用される結果になるでしょう。
ですので、最低でもその程度のスワップが利用可能にしておくのと、それに加えて変化するワークロードのために少しのバッファを持つことはおそらく有用でしょう。
また `atop` をロギングモードで使うと `SWAPSZ` カラムでどのアプリケーションがどれぐらいのページをスワップアウトされたか見ることができるので、もしあなたのサーバで歴史的なサーバの状態をログ出力するためにまだ `atop` を使っていない場合はおそらくあなたはこの実験の一部としてこれらのテストマシンに `atop` をロギングモードでセットアップすることをお勧めします。
これはまたあなたのアプリケーションが *いつ* ページのスワップアウトを開始したかを教えてくれますので、それをログイベントや他のキーデータと紐づけることができます。
<!--
If you're more constrained with disk space, then the answer really depends on
the tradeoffs you have to make, and the nature of the environment. Ideally you
should have enough swap to make your system operate optimally at normal and
peak (memory) load. What I'd recommend is setting up a few testing systems with
2-3GB of swap or more, and monitoring what happens over the course of a week or
so under varying (memory) load conditions. As long as you haven't encountered
severe memory starvation during that week -\- in which case the test will not
have been very useful -\- you will probably end up with some number of MB of
swap occupied. As such, it's probably worth having at least that much swap
available, in addition to a little buffer for changing workloads. `atop` in
logging mode can also show you which applications are having their pages
swapped out in the `SWAPSZ` column, so if you don't already use it on your
servers to log historic server state you probably want to set it up on these
test machines with logging mode as part of this experiment. This also tells you
*when* your application started swapping out pages, which you can tie to log
events or other key data.
-->

検討する価値のあるもう一つのことはスワップメディアの性質です。
どのページがいつ再フォールトするか正確に予想することはできないので、スワップの読み込みは非常にランダムになりがちです。
SSD ではこれはあまり問題になりませんが、回転ディスクでは物理的な移動を実行する必要があるのでランダム I/O は非常に高くつきます。
一方で、 file ページの再フォールトは比較的ランダムでない可能性が高いです。
というのは単一のアプリケーションが実行時に行う操作に関連するファイルは比較的断片化されていないからです。
これは回転ディスク上では、あなたは aononymous ページをスワップアウトする代わりに file ページを回収するようによりバイアスをかけたいと思うかもしれないことを意味します。
ですがこれもこのバランスがあなたのワークロードでどうなるかをテストおよび評価する必要があります。
<!--
Another thing worth considering is the nature of the swap medium. Swap reads
tend to be highly random, since we can't reliably predict which pages will be
refaulted and when. On an SSD this doesn't matter much, but on spinning disks,
random I/O is extremely expensive since it requires physical movement to
achieve. On the other hand, refaulting of file pages is likely less random,
since files related to the operation of a single application at runtime tend to
be less fragmented. This might mean that on a spinning disk you may  want to
bias more towards reclaiming file pages instead of swapping out anonymous
pages, but again, you need to test and evaluate how this balances out for your
workload.
-->

スワップにハイバネーションしたいラップトップとデスクトップのユーザにとってはそれを考慮に入れる必要があります。
この場合はスワップファイルは最低でもあなたの物理 RAM のサイズ以上にするべきです。
<!--
For laptop/desktop users who want to hibernate to swap, this also needs to be
taken into account -\- in this case your swap file should be at least your
physical RAM size.
-->

### swappiness の設定はどうするべきでしょうか？ <!-- What should my swappiness setting be? -->

まず、 `vm.swappiness` が何をするものかを理解することが重要です。
`vm.swappiness` はメモリ回収を anonymous ページの回収寄りにするのかあるいは file ページ寄りにするのかのバイアスを調整する sysctl です。
それはこれを `file_prio` （file ページを回収する優先度）と `anon_prio` ( anonymous ページを改選する優先度） という 2 つの異なる属性を使って行います。
`vm.swappiness` はその値が `anon_prio` のデフォルト値になり、また `file_prio` は 200 のデフォルト値から `vm.swappiness` の値を引いた値になります。
これは `vm.swappiness = 50` という値を設定した結果、 `anon_prio` は 50 になり、 `file_prio` は 150 になることを意味します（値そのものはあまり意味を持たず、もう片方との相対的な重みが意味を持ちます）。
<!--
First, it's important to understand what `vm.swappiness` does. `vm.swappiness`
is a sysctl that biases memory reclaim either towards reclamation of anonymous
pages, or towards file pages. It does this using two different attributes:
`file_prio` (our willingness to reclaim file pages) and `anon_prio` (our
willingness to reclaim anonymous pages). `vm.swappiness` plays into this, as it
becomes the default value for `anon_prio`, and it also is subtracted from the
default value of 200 for `file_prio`, which means for a value of
`vm.swappiness = 50`, the outcome is that `anon_prio` is 50, and `file_prio` is
150 (the exact numbers don't matter as much as their relative weight compared
to the other).
-->

これは、一般的には **vm.swappiness はあなたのハードウェアとワークロードに対して file メモリに比べて anonymous メモリを回収して再フォールトするのにどれぐらいのコストをかけるかの単なる比率である** ことを意味します。
値が小さいほど、あなたのハードウェアではアクセス頻度の低い anonymous ページをスワップアウトとスワップインするのは高くつくとカーネルにより強く伝えることになります。
値が大きいほど、あなたのハードウェアでは anonymous ページと file ページをスワップするコストは同程度であるとカーネルにより強く伝えることになります。
メモリ管理システムはこの値よりもまずはメモリがいかにホットであるかに基づいて file か anonymous メモリのどちらをスワップするかを主に決めようとするでしょう。
しかしそのどちらになってもおかしくないときに、コストの計算をスワップするほうに寄せるかあるいはファイルシステムのキャッシュをドロップするほうに寄せるかのどちらにするかに swappiness は寄与します。
SSD では基本的にどちらも同程度のコストなので `vm.swappiness = 100` （完全に平等）と設定することはうまく機能するかもしれません。
回転ディスクでは、スワップインは一般的にランダムリードを必要とするためスワッピングが著しく高くつくかもしれないので、より低い値にバイアスをかけたいと思うかもしれません。
<!--
This means that, in general, **vm.swappiness is simply a ratio of how costly
reclaiming and refaulting anonymous memory is compared to file memory for your
hardware and workload**. The lower the value, the more you tell the kernel that
infrequently accessed anonymous pages are expensive to swap out and in on your
hardware. The higher the value, the more you tell the kernel that the cost of
swapping anonymous pages and file pages is similar on your hardware. The memory
management subsystem will still try to mostly decide whether it swaps file or
anonymous pages based on how hot the memory is, but swappiness tips the cost
calculation either more towards swapping or more towards dropping filesystem
caches when it could go either way. On SSDs these are basically as expensive as
each other, so setting `vm.swappiness = 100` (full equality) may work well. On
spinning disks, swapping may be significantly more expensive since swapping in
generally requires random reads, so you may want to bias more towards a lower
value.
-->

現実にはほとんどの人は彼らのハードウェアの要求についてあまり意識していないのでこの値を直感だけに頼って調整するのは自明ではありません。
これは異なるいくつかの値を使って試してみる必要があるものなのです。
あなたのシステムとコアアプリケーションのメモリの構成と軽度のメモリ回収の状況下での振る舞いについて時間をかけて評価しても良いでしょう。
<!--
The reality is that most people don't really have a feeling about which their
hardware demands, so it's non-trivial to tune this value based on instinct
alone -\- this is something that you need to test using different values. You
can also spend time evaluating the memory composition of your system and core
applications and their behaviour under mild memory reclamation.
-->

`vm.swappiness` について話すときに、最近では考慮すべき非常に重要な変更があり、それは [2012 年に Satoru Moriya さんによって vmscan に行われたこの変更](https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux-stable.git/patch/?id=fe35004fbf9eaf67482b074a2e032abb9c89b1dd) です。
これは `vm.swappiness = 0` が処理される方法を非常に著しく変更します。
<!--
When talking about `vm.swappiness`, an extremely important change to consider
from recent(ish) times is [this change to vmscan by Satoru Moriya in
2012](https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux-stable.git/patch/?id=fe35004fbf9eaf67482b074a2e032abb9c89b1dd),
which changes the way that `vm.swappiness = 0` is handled quite significantly.
-->

実質的には、このパッチは `vm.swappiness = 0` と設定すると、深刻なメモリ争奪に既に出くわしているのではない限り、 anonymous ページをスキャン（そして回収）することを極端に避けるようにバイアスをかけます。
この記事で既に述べたように、これは一般的にはあなたが望むものではないでしょう。
というのは極端なメモリ逼迫が発生する前に回収の平等さを妨げるものであり、それが実はそもそもの極端なメモリ逼迫を *引き起こす* かもしれないからです。
このパッチで実装されている anonymous ページのスキャンの特別な場合分けを実行しないようにするには `vm.swappiness = 1` が設定可能な最小値です。
<!--
Essentially, the patch makes it so that we are extremely biased against
scanning (and thus reclaiming) any anonymous pages at all with
`vm.swappiness = 0`, unless we are already encountering severe memory
contention. As mentioned previously in this post, that's generally not what you
want, since this prevents equality of reclamation prior to extreme memory
pressure occurring, which may actually *lead* to this extreme memory pressure
in the first place. `vm.swappiness = 1` is the lowest you can go without
invoking the special casing for anonymous page scanning implemented in that
patch.
-->

ここでのカーネルのデフォルト値は `vm.swappiness = 60` です。
一般的にはこの値はほとんどのワークロードではそれほど悪くはありませんが、全てのワークロードに適した一般的なデフォルト値を持つことは難しいものです。
ですので、上記の「ではスワップのサイズはどれぐらい必要なのでしょう？」の項で言及した調整への有用な延長は vm.swappiness のいくつかの異なる値でこれらのシステムをテストし、あなたのアプリケーションとシステムのメトリクスを大量の（メモリ）負荷のもとでモニタリングすることでしょう。
近い将来、私たちがカーネル内に [再フォールト検知](https://youtu.be/ikZ8_mRotT4?t=2145) のまともな実装を持つようになったら、 cgroup v2 のページ再フォールトメトリックを見ることでこのワークロードの検知がいまいちわからなかったのがわかるようになるでしょう。
<!--
The kernel default here is `vm.swappiness = 60`. This value is generally not
too bad for most workloads, but it's hard to have a general default that suits
all workloads. As such, a valuable extension to the tuning mentioned in the
"how much swap do I need" section above would be to test these systems with
differing values for vm.swappiness, and monitor your application and system
metrics under heavy (memory) load. Some time in the near future, once we have a
decent implementation of [refault
detection](https://youtu.be/ikZ8_mRotT4?t=2145) in the kernel, you'll also be
able to determine this somewhat workload-agnostically by looking at cgroup v2's
page refaulting metrics.
-->

### 2019-07 更新: カーネル 4.20+ でのメモリ逼迫メトリクス <!-- Update as of 2019-07: memory pressure metrics in kernel 4.20+ -->


上述の以前開発中だった再フォールトのメトリクスが 4.20 以降のカーネルには入っており、 `CONFIG_PSI=y` で有効にできます。
SREcon での私の講演の 25:05 付近を参照してください。
<!--
The refault metrics mentioned as in development earlier are now in the kernel
from 4.20 onwards and can be enabled with `CONFIG_PSI=y`. See my talk at SREcon
at around the 25:05 mark:
-->

{% youtube beefUhRH5lU %}

## 結論 <!-- In conclusion -->

- スワップはメモリページの回収の平等さを許可する有用なツールですが、その目的はしばしば誤解されており、業界内でのネガティブな認知につながっています。
  意図されたとおりに、つまり回収の平等さを増やすための方法として、スワップを使えば、あなたはスワップを禁止するのではなく有用なツールであると気づくでしょう。
  <!-- Swap is a useful tool to allow equality of reclamation of memory pages, but
  its purpose is frequently misunderstood, leading to its negative perception
  across the industry. If you use swap in the spirit intended, though -\- as a
  method of increasing equality of reclamation -\- you'll find that it's a
  useful tool instead of a hindrance. -->
- スワップを無効にすることはメモリ争奪の状況下においてディスク I/O が問題になることを防いでくれるわけではありません。
  単に anonymous ページのスラッシングのディスク I/O を file ページのそれにシフトするだけです。
  これはより非効率なだけでなく、回収元の選択肢のページプールが小さくなるのでそもそものメモリ争奪の状態が起きやすくなることに寄与してしまうかもしれません。
  <!-- Disabling swap does not prevent disk I/O from becoming a problem under memory
  contention, it simply shifts the disk I/O thrashing from anonymous pages to
  file pages. Not only may this be less efficient, as we have a smaller pool of
  pages to select from for reclaim, but it may also contribute to getting into
  this high contention state in the first place. -->
- スワップは OOM キルの発生を遅らせることができます。
  というのはスワップはメモリを使い果たした状況下でメモリをスラッシングする別の遅いソースを提供するからです。
  OOM キラーは状況が途方もなくめちゃくちゃになってから後の手段としてしかカーネルに使われません。
  ここでの解決策はあなたのシステムによって異なります。
  <!-- Swap can make a system slower to OOM kill, since it provides another, slower
  source of memory to thrash on in out of memory situations -\- the OOM killer
  is only used by the kernel as a last resort, after things have already become
  monumentally screwed. The solutions here depend on your system: -->
    - cgroup ローカルかあるいはグローバルのメモリ逼迫に依存したシステムのワークロードを機会に応じて変えることができます。
      これはそもそもこれらの状況になることを防いでくれますが、メモリ逼迫についてのしっかりとしたメトリクスは Unix の歴史には欠乏していました。
      幸いにも [再フォールト検出](https://youtu.be/ikZ8_mRotT4?t=2145) の追加によってこれはまもなく改善されるでしょう。
      <!-- You can opportunistically change the system workload depending on
      cgroup-local or global memory pressure. This prevents getting into these
      situations in the first place, but solid memory pressure metrics are
      lacking throughout the history of Unix. Hopefully this should be better
      soon with the addition of [refault
      detection](https://youtu.be/ikZ8_mRotT4?t=2145). -->
    - `memory.low` と使うことで cgroup 毎の特定のプロセスから回収（そしてスワップ）させないようにバイアスをかけることができ、その結果スワップ全体を無効にすることなくクリティカルなデーモンを保護することができます。
      <!-- You can bias reclaiming (and thus swapping) away from certain processes
      per-cgroup using `memory.low`, allowing you to protect critical daemons
      without disabling swap entirely. -->

---

この記事への幅広い提案とフィードバックに関して [Rahul](https://github.com/rahulg), [Tejun](https://github.com/htejun), そして [Johannes](https://patchwork.kernel.org/project/LKML/list/?submitter=45) に多大なる感謝を。
<!--
Many thanks to [Rahul](https://github.com/rahulg),
[Tejun](https://github.com/htejun), and
[Johannes](https://patchwork.kernel.org/project/LKML/list/?submitter=45) for
their extensive suggestions and feedback on this post.
-->
