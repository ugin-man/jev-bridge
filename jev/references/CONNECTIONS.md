# 接続と保存先

## 通常：スキル内のスクリプト

`jev/scripts/jev.py` と `_vendor/jev_core.py` だけで動く。Python 3.11以上の標準ライブラリを使い、pip/npmや別のOpenAI APIキーは必要ない。自然文の解釈はホストのLLMが行い、スクリプトは検査とTypeSafeへの要求を行う。

保存先は次の順で選ぶ。

1. ローカルで明示された環境変数 JEV_SKILL_HOME、JEV_WORKER_HOME、JEV_HELPER_HOME の順。
2. CODEX_HOME（未指定ならユーザーの .codex）の tools/jev-worker、tools/jev-helper のうち、暗号化済みキーがある最初の場所。
3. その2つのうち、すでに存在する最初のフォルダー。
4. どちらもなければ同じCODEX_HOME配下の tools/jev-skill。

キーの値を見せずに、statusのstorage_homeで選択結果を確認できる。元のキー・設定・使用量ファイルをコピーしない。同じ保存先なら日次カウンターを共用する。既存キーを更新するとその保存先を使うWorker/Helperにも影響するので、既存キーが使える場合はSET-KEYを不要に実行しない。

スキルのインストール先は $HOME/.agents/skills/jev。CODEX_HOMEとは別で、これはCodexの公式ローカルスキル探索先に合わせたもの。スキルを入れてもモデルやMCPの設定は変えない。

## 既存MCPがすでに使える場合のみ

通常は上記スクリプトでよい。ホストの制約などからMCPを利用するなら、まず実際に露出しているツールとスキーマを確認する。接続先が変われば設定・保存先も違う場合がある。上限や承認の回避に使わない。

Jev Helper 1.0.0では `jev_status`、`jev_evaluate`、`jev_batch` 等。`jev_evaluate` はstate/questions/dry_run、`jev_batch` はitems/questions/dry_run。構造化結果の中に answers がある。返った実際のスキーマを優先する。

Jev Worker 0.2.0だけの場合は、状態を持つ手順が必要なときに限り次の2ノードへ変換できる。

```json
{
  "plan": {
    "version": 1,
    "name": "one-evaluation",
    "entry": "evaluate",
    "nodes": {
      "evaluate": {
        "op": "evaluate",
        "state": {"$ref": "/input"},
        "questions": {
          "red": {"type": "noul", "instructions": "商品は赤色だと記載されていますか？"}
        },
        "save": "judgments",
        "next": "finish"
      },
      "finish": {"op": "finish", "output": {"$ref": "/vars/judgments"}}
    }
  },
  "input": "赤いマグカップ"
}
```

実ツールのvalidate(plan,input)を呼び、初回の無通信検査ではcreate(plan,input,live=false)→run(job_id)を使う。dry_run_pausedは成功した判定ではない。実APIへの許可がある場合だけ、新しくlive=trueのジョブを作る。既存dry-runを勝手に本番へ変えない。
createのIDは `job.id`。runは `job` を返す。`completed`を確認して `job.output` を読み、必要ならget(include_state=true)を使う。handoff/failed等を正常完了としない。外側の `ok:true` だけで判断しない。

このスキルはMCP登録・独立プロファイル・モデル一覧の追加を行わない。前のWorkerのインストールも、このスキルには必須ではない。

## デスクトップでの呼び出し

名前を含めて「Jevスキルを使って」と頼む方法を基本にする。ホストにより、ChatGPT側の選択は@、Codex CLI/IDEは$や/skills。UIの呼び出し文字を全環境で同じと断言しない。表示されない場合はスキルのパス・フロントマター・実アプリの探索先を確かめる。必要ならアプリを再起動する。

公式： https://learn.chatgpt.com/docs/build-skills

TypeSafe自身も開発者向けのエージェントスキルを公開している。本パッケージはその複製ではなく、今回の「利用者にプログラムを書かせずに実行する」ための独立した日本語ワークフロー。
公式の案内： https://docs.typesafe.ai/agent-skill
