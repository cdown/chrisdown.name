---
layout: post
title: "大規模システムでの Linux のメモリ管理"
lang: ja
translations:
    - lang: en
      url: /2019/07/18/linux-memory-management-at-scale.html
redirect_from:
    - /swap-ja/

# Otherwise the english is the desc
description: "これらの会話を通じてどんどん明らかになってきた 1 つの事実は多くのエンジニアは、シニア SRE たちでさえも、 Linux のメモリ管理についていくつかのよくある誤解を持っていて、そしてそれが彼らがサポートするサービスやシステムが本来確実に稼働したり効率的に稼働したりできていたはずのところをそうできていない原因になっているということです。"
---

[(This post is also available in
English.)](/2019/07/18/linux-memory-management-at-scale.html)

この記事は [Linux memory management at scale](https://chrisdown.name/2019/07/18/linux-memory-management-at-scale.html) を [著者の Chris Down さんの許可](https://twitter.com/unixchris/status/1224285773660377089) を得て [Hiroaki Nakamura](https://github.com/hnakamur/) が日本語に翻訳したものです。 [原文のライセンス](https://github.com/cdown/chrisdown.name/blob/master/LICENSE) は [CC BY-SA 4.0](http://creativecommons.org/licenses/by-sa/4.0/) であり、翻訳のライセンスも同じく CC BY 4.0 とします。

---

[cgroup2](https://facebookmicrosites.github.io/cgroup2/) プロジェクトでの私の仕事の一部として Linux システムのリソース管理についてエンジニアと話すことに多くの時間をかけてきました。
これらの会話を通じてどんどん明らかになってきた 1 つの事実は多くのエンジニアは、シニア SRE たちでさえも、 Linux のメモリ管理についていくつかのよくある誤解を持っていて、そしてそれが彼らがサポートするサービスやシステムが本来確実に稼働したり効率的に稼働したりできていたはずのところをそうできていない原因になっているということです。
<!--
As part of my work on the
[cgroup2](https://facebookmicrosites.github.io/cgroup2/) project, I spend a lot
of time talking with engineers about controlling resources across Linux
systems. One thing that has become clearer and clearer to me through these
conversations is that many engineers -\- and even senior SREs -\- have a number
of common misconceptions about Linux memory management, and this may be causing
the services and systems they support to not be able to run as reliably or
efficiently as they could be.
-->

ですので、これらの誤解の一部に踏み込む講演を行いました。
そこではメモリのこととなると一見そう見えるよりも事態がなぜ微妙なニュアンスを持つのかに踏み込んでいます。
さらに私はこの新しい知識を使ってより信頼性が高くスケーラブルなシステムをどうやって構成するかについても調べ、 Facebook でどのようにシステムを管理しているか、そしてあなた自身のシステムを改善するためにこの知識をどう応用することができるかについても話しています。
<!--
As such, I wrote a talk which goes into some of these misconceptions, going
into why things are more nuanced than they might seem when it comes to memory.
I also go over how to compose more reliable and scalable systems using this new
knowledge, talking about how we are managing systems within Facebook, and how
you can apply this knowledge to improve your own systems.
-->

私は光栄にも SREcon でこの講演をしました。
これが役に立つことを願っています。
質問やコメントがあればご自由に私に e-mail を送ってください。
<!--
I had the privilege to present this talk at SREcon, and hope you'll find it
useful. Please feel free to e-mail me with any questions or comments.
-->

{% youtube beefUhRH5lU %}

## 鍵となるタイムスタンプ <!-- Key timestamps -->

各セクションがその次のセクションを構成するのに役立ちますので講演全体を見ることをお勧めしますが、いくつかのキーポイントとなる箇所を以下に示します。
<!--
I recommend watching the whole talk, since each section helps set up the next, but here are some key takeaways:
-->

- 2:18: [リソース管理は重要であり、信頼性と効率性の両方のために必要です](https://youtu.be/beefUhRH5lU?t=138) <!-- [Resource control is important, you need it both for reliability and efficiency](https://youtu.be/beefUhRH5lU?t=138) -->
- 6:34: [単一のリソースだけにリミットをかけると、事態は悪化するかもしれません](https://youtu.be/beefUhRH5lU?t=395) <!-- [If you just limit one resource alone, it may actually make things worse](https://youtu.be/beefUhRH5lU?t=395) -->
- 7:28: [リソース管理は一見するよりもはるかに複雑なものです](https://youtu.be/beefUhRH5lU?t=448) <!-- [Resource control is much more complicated than it seems](https://youtu.be/beefUhRH5lU?t=448) -->
- 12:56: [多くの人々が誤解していますが、「回収可能」であるということは保証ではなく、キャッシュやバッファはフリーメモリのようには振る舞いません](https://youtu.be/beefUhRH5lU?t=776) <!-- [Being "reclaimable" isn't a guarantee, caches and buffers don't act like free memory, even though many people think they do](https://youtu.be/beefUhRH5lU?t=776) -->
- 14:54: [私たちは RSS を計測しそれに意味があるふりをしていますが、それは簡単に計測できるからであって、有用な何かを測れるものだからではありません](https://youtu.be/beefUhRH5lU?t=894) <!-- [We measure RSS and pretend it's meaningful because it's easy to measure, not because it measures anything useful](https://youtu.be/beefUhRH5lU?t=894) -->
- 16:12: [巨大なメモリを持つマシンでさえ、スワップは重要です](https://youtu.be/beefUhRH5lU?t=972) <!-- [Swap matters, even on machines with huge amounts of memory](https://youtu.be/beefUhRH5lU?t=972) -->
- 18:59: [OOM キラーは OOM の状況下でもあなたの友達ではないですし、あなたが期待するようにはたぶん動かないでしょう](https://youtu.be/beefUhRH5lU?t=1139) <!-- [The OOM killer is often not your friend in an OOM situation, and probably doesn't work in the way you expect](https://youtu.be/beefUhRH5lU?t=1139) -->
- 22:10: [メモリ回収の異なる種別となぜそれが重要か](https://youtu.be/beefUhRH5lU?t=1330) <!-- [Different types of memory reclaim and why they matter](https://youtu.be/beefUhRH5lU?t=1330) -->
- 25:05: [システムがメモリを使い果たしたかをどのように知るか（単に MemAvailable あるいは MemFree + Buffers + Cached を見てもわかりません）](https://youtu.be/beefUhRH5lU?t=1505) <!-- [How to know if a system is running out of memory (you can't just look at MemAvailable or MemFree + Buffers + Cached)](https://youtu.be/beefUhRH5lU?t=1505) -->
- 29:30: [どのようにして OOM キラーの前に迫りつつある OOM を検知するか](https://youtu.be/beefUhRH5lU?t=1770) <!-- [How we detect emerging OOMs before the OOM killer](https://youtu.be/beefUhRH5lU?t=1770) -->
- 30:49: [I/O リソースの分離に有用なメトリックの決定](https://youtu.be/beefUhRH5lU?t=1849) <!-- [Determining a usable metric for I/O resource isolation](https://youtu.be/beefUhRH5lU?t=1849) -->
- 34:42: [何かにリミットをかけることは一般的にはうまく行かないので代わりに保護を作りましょう](https://youtu.be/beefUhRH5lU?t=2082) <!-- [Limiting things generally doesn't work well, so let's create protections instead](https://youtu.be/beefUhRH5lU?t=2082) -->
- 37:21: [これらのプリミティブを全て組み合わせれば効率の良いハイアベイラビリティなシステムを作れます](https://youtu.be/beefUhRH5lU?t=2241) <!-- [Putting all of these primitives together to create an efficient, high availability system](https://youtu.be/beefUhRH5lU?t=2241) -->
- 46:09: [Facebook での本番運用での結果](https://youtu.be/beefUhRH5lU?t=2769) <!-- [Results from Facebook production](https://youtu.be/beefUhRH5lU?t=2769) -->
- 48:03: [これらの新しい概念のいくつかを使って Android の改善に役立てる](https://youtu.be/beefUhRH5lU?t=2883) <!-- [Using some of these new concepts to help improve Android](https://youtu.be/beefUhRH5lU?t=2883) -->
- 48:53: [この講演のアドバイスをあなた自身でどのようにして実際に利用するか](https://youtu.be/beefUhRH5lU?t=2933) <!-- [How to practically make use of the advice in this talk yourself](https://youtu.be/beefUhRH5lU?t=2933) -->
