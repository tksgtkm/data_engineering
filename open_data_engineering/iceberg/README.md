## IAM ユーザーにアクセス権限を付与する
takumi_test1 ユーザーに S3 の権限を与えます。
① IAM コンソールを開く

AWS コンソール → 検索バーに「IAM」→ IAM を開く

② ユーザーを選択

左メニュー「ユーザー」→ takumi_test1 をクリック

③ 権限を追加

「許可を追加」ボタン → 「許可を追加」を選択
「ポリシーを直接アタッチする」を選択
検索欄に AmazonS3FullAccess と入力 → チェックを入れる
「次へ」→「許可を追加」

④ アクセスキーを発行

takumi_test1 のページに戻る
「セキュリティ認証情報」タブ → 「アクセスキーを作成」
ユースケースは 「ローカルコード」 を選択
キーが表示されたら CSV をダウンロード（この画面を閉じると二度と見れません）

## Javaのインストール
① Java 11 のインストール
sudo apt update
sudo apt install openjdk-11-jdk -y

② インストール確認
java -version
以下のように表示されればOKです：
openjdk version "11.x.x" ...

③ JAVA_HOME の設定
echo 'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64' >> ~/.bashrc
echo 'export PATH=$JAVA_HOME/bin:$PATH' >> ~/.bashrc
source ~/.bashrc

## pyspark
pip install pyspark==3.5.4