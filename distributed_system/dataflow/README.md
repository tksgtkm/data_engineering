protoc ProtocolBuffer を入れる

cd /tmp
curl -LO https://github.com/protocolbuffers/protobuf/releases/download/v25.3/protoc-25.3-linux-x86_64.zip
sudo unzip -o protoc-25.3-linux-x86_64.zip -d /usr/local
sudo chmod +x /usr/local/bin/protoc
protoc --version

go言語
go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

echo 'export PATH="$PATH:$(go env GOPATH)/bin"' >> ~/.bashrc
source ~/.bashrc

protoc-gen-go --version
protoc-gen-go-grpc --version

protoc -I ../proto \
  ../proto/product_info.proto \
  --go_out=./gen/ecommerce --go_opt=paths=source_relative \
  --go-grpc_out=./gen/ecommerce --go-grpc_opt=paths=source_relative
