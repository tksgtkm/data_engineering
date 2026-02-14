package server

import (
	"context"
	"log"
	"net"
	"sync"

	pb "productinfo/gen/ecommerce"

	"github.com/gofrs/uuid"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

const port = ":50051"

type server struct {
	pb.UnimplementedProductInfoServer

	mu         sync.RWMutex
	productMap map[string]*pb.Product
}

func newServer() *server {
	return &server{
		productMap: make(map[string]*pb.Product),
	}
}

func (s *server) AddProduct(ctx context.Context, in *pb.Product) (*pb.ProductID, error) {
	id, err := uuid.NewV4()
	if err != nil {
		return nil, status.Errorf(codes.Internal, "failed to generate product id: %v", err)
	}

	p := &pb.Product{
		Id:          id.String(),
		Name:        in.GetName(),
		Description: in.GetDescription(),
		Price:       in.GetPrice(),
	}

	s.mu.Lock()
	s.productMap[p.Id] = p
	s.mu.Unlock()

	log.Printf("Product %s: %s - added", p.Id, p.Name)
	return &pb.ProductID{Value: p.Id}, nil
}

func (s *server) GetProduct(ctx context.Context, in *pb.ProductID) (*pb.Product, error) {
	key := in.GetValue()

	s.mu.RLock()
	p, ok := s.productMap[key]
	s.mu.RUnlock()

	if !ok || p == nil {
		return nil, status.Errorf(codes.NotFound, "product does not exist: %s", key)
	}

	log.Printf("Product %s: %s - retrieved", p.Id, p.Name)
	return p, nil
}

func main() {
	lis, err := net.Listen("tcp", port)
	if err != nil {
		log.Fatalf("listen failed: %v", err)
	}

	grpcServer := grpc.NewServer()
	pb.RegisterProductInfoServer(grpcServer, newServer())

	log.Printf("gRPC server listening on %s", port)
	if err := grpcServer.Serve(lis); err != nil {
		log.Fatalf("serve failed: %v", err)
	}
}
