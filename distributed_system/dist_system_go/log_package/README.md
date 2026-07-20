# log_package

Go による分散システム学習用のコミットログ実装。

## 動作環境

- OS: Ubuntu Linux
- Go: 1.25(手動インストール、`/usr/local/go`)
- Protocol Buffers: protoc 28.3(手動インストール、`/usr/local/protobuf`)

## セットアップ

### 1. Go のインストール

apt 版の Go(1.22.x)は古いため削除し、公式バイナリを `/usr/local/go` に配置する。

```bash
sudo apt remove golang-go   # apt 版が入っている場合
# 公式サイトから tarball を取得して展開
sudo tar -C /usr/local -xzf go1.25.x.linux-amd64.tar.gz
```

`~/.profile` に PATH を追加:

```bash
export PATH="$PATH:/usr/local/go/bin"
```

### 2. protoc のインストール

公式リリースの zip を `/usr/local/protobuf` に展開し、PATH を追加する。

```bash
export PATH="$PATH:/usr/local/protobuf/bin"
```

> **注意**: `/usr/local/bin/protoc` など古い protoc が PATH 上に残っていると
> そちらが優先される。`type -a protoc` で確認し、不要なものは削除する。

### 3. protoc-gen-go プラグインのインストール

protoc が Go コードを生成するためのプラグイン。protoc 本体とは別に必要。

```bash
go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
```

バイナリは `$(go env GOPATH)/bin`(通常 `~/go/bin`)に入るため、
`~/.profile` に PATH を追加する:

```bash
export PATH="$PATH:$HOME/go/bin"
```

追加後はシェルを再読み込み:

```bash
source ~/.profile
hash -r
type -a protoc-gen-go   # ~/go/bin/protoc-gen-go が表示されればOK
```

gRPC サービス定義もコンパイルする場合は以下も必要:

```bash
go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest
```

### 4. 依存モジュールの取得

生成された `*.pb.go` は `google.golang.org/protobuf` ランタイムに依存する。
`go.mod` に依存を反映するには:

```bash
go mod tidy
```

## ビルドとテスト

### .proto ファイルのコンパイル

```bash
make compile
```

内部では以下を実行している:

```bash
protoc api/v1/*.proto \
    --go_out=. \
    --go_opt=paths=source_relative \
    --proto_path=.
```

### テストの実行

```bash
make test
```

内部では `go test -race ./...` を実行(データ競合検出付き)。

## トラブルシューティング

| 症状 | 原因 | 対処 |
|---|---|---|
| `protoc-gen-go: program not found` | プラグイン未インストール、または `~/go/bin` が PATH に無い | `go install` 後、`~/.profile` に PATH を追加して `source ~/.profile` |
| `no required module provides package google.golang.org/protobuf/...` | 生成コードの依存が `go.mod` に未登録 | `go mod tidy` |
| 古いバージョンのツールが実行される | PATH 上で古いバイナリが先に見つかっている | `type -a <tool>` で場所を確認し、古い方を削除して `hash -r` |
| PATH 変更が反映されない | シェルセッションが再読み込みされていない | `source ~/.profile` するか新しいログインシェルを開く |
| `type -a` で PATH が二重に見える | セッション途中で `~/.profile` を再 source した影響 | 見た目だけの問題。新規ログインで解消 |