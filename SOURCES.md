# 参照仕様と同梱コード

元パッケージの仕様確認日：2026-09-17。

- OpenAI公式スキル形式・探索先：https://developers.openai.com/codex/skills/
- OpenAI公式スキル案内：https://learn.chatgpt.com/docs/build-skills
- TypeSafe API：https://docs.typesafe.ai/api
- Choice：https://docs.typesafe.ai/primitives/choice
- Score：https://docs.typesafe.ai/primitives/score
- Noul：https://docs.typesafe.ai/primitives/noul
- TypeSafeのエージェントスキル案内：https://docs.typesafe.ai/agent-skill

このリポジトリは非公式の日本語操作スキルであり、公式スキルのコピーや自動インストールではない。

## 取り込み元

`jev-natural-skill-v1.0.0.zip`

SHA-256: `62d96e85dedbed164ee71731fc5e90a5cfd321425f0764a48c4667374411a39a`

`jev/scripts/_vendor/jev_core.py`は、以前作成したJev Worker 0.2.0から再利用された独自クライアント。公式SDKではなく、Python標準ライブラリによるHTTP・検証・DPAPI・使用量管理を行う。今回のリポジトリへの転記後も、実行用Pythonコード3ファイルのGit blobハッシュがローカルの元ファイルと一致することを確認した。

古いZIP用のチェックサム一覧と過去のテストログは、新しいリポジトリ全体の検証結果と紛らわしくなるため取り込んでいない。APIキー、利用者のメール、会話履歴、画像、モデル重み、アプリ本体も含めていない。

LICENSE.txtは元の配布物の注記を保持したものであり、この取り込みで新たなOSSライセンスを選定していない。
