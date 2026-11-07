# FM Dev Process Skills

**A document-first software development process built around a small team of dedicated AI workers.** Instead of asking one agent to do every specialist job, FM Dev Process assigns planning, implementation, testing, review, and acceptance to distinct roles and has a top-level leader coordinate their work.

[日本語](#日本語) · [English](#english)

## 日本語

### これは何？

FM Dev Process は、専属の専門ワーカーを持つ小さなソフトウェア開発チームを AI agent 上でシミュレートするための、役割別 Skills と開発プロセス文書です。要求整理、設計、実装、テスト、独立受け入れを役割として分け、合意した成果と確認結果をファイルに残しながら進めます。

単なる「順番にプロンプトを呼ぶ」テンプレートではありません。leader が必要な専門作業を実際の subagent に委譲し、結果・成果物・進捗記録を照合することを前提とします。

作業内容に問題があり、受け入れ不可と判断されたら実装に戻り合格するまで繰り返す設計になっています。このループ機構が全体にかかっているので、要求を満たす（もしくは進行できなくなる）まで停止せず、かつ検査済みのコードの完成まで進みます。

### 12の役割

| Skill | 担当 |
| --- | --- |
| `fm-dev-process` | 一連の工程を調整し、計画と実装を切り替えるトップレベルのleader |
| `fm-dev-plan` | 初回計画、または範囲を絞った再計画を進めるleader |
| `fm-dev-implement` | 計画に沿って作業分解、実装、確認、独立受け入れ、完了処理を調整するleader |
| `fm-dev-requirement` | 目的・範囲・要求・受け入れ条件を整理 |
| `fm-dev-cheatsheet` | 技術やドメインを調査し、再利用可能な知見を記録 |
| `fm-dev-architect` | 構造・振る舞い・インターフェースを設計 |
| `fm-dev-taskplanner` | 作業単位・依存関係・完了条件を計画 |
| `fm-dev-reviewer` | 次の作業へ進める計画かを独立に確認 |
| `fm-dev-develop` | 割り当てられた実装・統合と内部確認を担当 |
| `fm-dev-tester` | テストを設計・作成・実行し、観測結果を報告 |
| `fm-dev-acceptance` | 合意した条件に対して実装成果を独立に判定 |
| `fm-dev-release` | 確認済み成果の文書反映と引き渡しを担当 |

### 基本の考え方

- **役割を分ける:** leader は進行を管理し、専門作業は対応する specialist worker に委譲します。
- **委譲は1段:** トップレベルのagentがleader業務を担い、専門役をsubagentとして起動します。subagentの入れ子起動は前提にしません。
- **プラン文書を作成する:** 何を作るかを毎回プランドキュメントとして作成、 Patch / Light / Full の区分に応じて記録します。
- **どこまで進行したかを記録する:** Light / Full では `90_status.md` が進捗を記したログです。Patch では合意した引き渡し記録を使います。
- **実装と受け入れを分ける:** 実装者の自己確認を独立した受け入れ判定の代わりにしません。
- **事実と判定を分ける:** 実際に確認した範囲と証跡を記録し、未確認を成功扱いしません。
- **規模に合わせる:** すべての依頼で全役を起動したり、Full の文書一式を作ったりするわけではありません。

### 入手

```bash
git clone https://github.com/rerofumi/fm-dev-process-skills.git
```

リポジトリページの **Code → Download ZIP** からも取得できます。入手後は、次の「使い始める」へ進んでください。

### 使い始める

1. `skills/fm-dev-*` の **12ディレクトリすべて**を、利用するagent runtimeが認識するskillsディレクトリへ配置します。相対参照があるため、各ディレクトリを同じ親の下に置いてください。ランタイム固有の配置場所・登録方法は、そのランタイムの公式ドキュメントに従ってください。
2. 利用するagentで、必要なsubagentを実際に起動できることを確認します。`fm-dev-process`、`fm-dev-plan`、`fm-dev-implement` はトップレベルのagentがleaderとして実行します。専門作業は、それぞれの専門Skillを指定したsubagentへ委譲します。
3. 要望に応じて入口を選びます。
   - 最初から計画・実装を一貫して依頼する: `fm-dev-process`
   - 計画だけ作成・確認する: `fm-dev-plan`
   - `ready` な計画から実装を進める: `fm-dev-implement`
4. 最初の依頼に対象リポジトリ、作業場所、目的、維持条件、分かっている制約を含めます。既存計画がある場合は、計画と現在の進捗記録の場所も指定します。

**重要:** 利用環境がsubagentを起動できない場合、このプロセスの委譲要件は満たされません。専門作業をleader自身が実施したことにせず、未実行の作業と再開条件を報告してください。

### 具体的な使い方

- `数当てゲームを作成してください、 fm-dev-process skill を使用し Full tier でプランを作成します。`
  - 作りたいものをプロンプトやメモファイルに記載し、あとは process skill にお任せするパターン
  - Light / Full ではプランドキュメントの量が変わります。今回作ったり修正するものの規模に合わせて指定するとよいオプションです
- `行き詰まった時に押すヒントボタンを追加してください、fm-dev-plan skill を使用し Light tier でプランを作成します。`
  - 実装前にプランドキュメントを作成し、そこで一旦停止するパターン
  - 何を作るか、方向性が間違っていないか、要求の理解は正しいかといったレビューをして Go を出してから実装を開始するといったユーザー確認を挟みます
  - どうやって作るかといった調査にも使えると思います
- `docs/plan_YYYYMMDD_implement_plan を fm-dev-process skill に沿って、実装を行ってください。`
  - プランドキュメントのレビューが終わった後、実装を開始したいときにはこのパターンで依頼します
  - 実装を行う leader skill は fm-dev-implement ですが実装中に仕様の不備があった場合 fm-dev-plan に戻ることがあります。そのやり直しループを行うためトップ leader である fm-dev-process の方が有効です
  - 途中まで実装、中断していたものを再開するという場合もこの指定で大丈夫です

### ドキュメント

- [開発プロセスの入口・役割一覧・読み始めガイド](docs/develop_document/00_index.md)
- [共通プロンプトと実行契約](docs/develop_document/00_common.md)
- [文書の役割と記録形式](docs/develop_document/00_documents.md)
- [配布Skill一覧](skills/)
- [更新履歴](docs/develop_document/UPDATE.md)

各 `fm-dev-*` の開発原稿は `docs/develop_document/`、利用するSkill本体・参照資料・補助スクリプトは `skills/` にあります。補助の `artifact_identity.py` は任意で、使う場合のみPython 3.10以上が必要です。詳しくは[ツールの説明](docs/develop_document/artifact-identity.md)を参照してください。

## English

FM Dev Process Skills is a document-first software development workflow that simulates a small team of dedicated AI workers. It separates leadership from specialist work—requirements, architecture, task planning, development, testing, review, independent acceptance, and release handoff—so that decisions, evidence, and progress can be checked rather than inferred from a single agent's claim.

Get the files with `git clone https://github.com/rerofumi/fm-dev-process-skills.git`, or use **Code → Download ZIP** on the repository page, then place the 12 directories from `skills/` as described below.

The repository contains **12 complementary skills**: `fm-dev-process`, `fm-dev-plan`, `fm-dev-implement`, and nine specialist skills. Install all 12 as sibling directories under the skill location recognized by your agent runtime; individual skills rely on shared references in `fm-dev-process`. The top-level agent performs leader duties and delegates specialist work to subagents one level deep. A runtime that cannot launch subagents cannot satisfy this workflow's delegation contract.

Choose `fm-dev-process` for end-to-end coordination, `fm-dev-plan` for planning alone, or `fm-dev-implement` to execute an existing ready plan. Light and Full work use `90_status.md` as the single progress record; Patch work uses an agreed handoff record. The process does not require every specialist or every document for every task.

See the [process guide](docs/develop_document/00_index.md), [shared execution contract](docs/develop_document/00_common.md), and [document conventions](docs/develop_document/00_documents.md). The optional artifact identity helper requires Python 3.10+ only when you choose to use it.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Process changes should keep the development-source documents and packaged skills aligned.

## License

[MIT](LICENSE).

Copyright (c) 2026 rerofumi
