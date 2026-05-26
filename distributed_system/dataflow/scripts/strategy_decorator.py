promos = []

def promotion(promo_func):
    promos.append(promo_func)
    return promo_func

@promotion
def fidelity(order):
    return order.total() * .05 if order.customer.fidelity >= 1000 else 0

@promotion
def bulk_item(order):
    discount = 0
    for item in order.cart:
        if item.quantity >= 20:
            discount += item.total() * .1
    return discount

@promotion
def large_order(order):
    distinct_items = {item.product for item in order.cart}
    if len(distinct_items) >= 10:
        return order.total() * .07
    return 0

def best_promo(order):
    return max(promo(order) for promo in promos)

if __name__ == '__main__':
    from collections import namedtuple

    Customer = namedtuple('Customer', 'name fidelity')

    class LineItem:

        def __init__(self, product, quantity, price):
            self.product = product
            self.quantity = quantity
            self.price = price
        
        def total(self):
            return self.price * self.quantity
    
    class Order:

        def __init__(self, customer, cart, promotion=None):
            self.customer = customer
            self.cart = list(cart)
            self.promotion = promotion
        
        def total(self):
            if not hasattr(self, '__total'):
                self.__total = sum(item.total() for item in self.cart)
            return self.__total
        
        def due(self):
            if self.promotion is None:
                discount = 0
            else:
                discount = self.promotion(self)
            return self.total() - discount
        
        def __repr__(self):
            fmt = '<Order total: {:.2f} due: {:.2f}>'
            return fmt.format(self.total(), self.due())
    
    joe = Customer('John Doe', 0)
    ann = Customer('Ann Smith', 1100)
    cart = [
        LineItem('banana', 4, .5),
        LineItem('apple', 10, .5),
        LineItem('watermellon', 5, 5.0)
    ]
    
    print(Order(joe, cart, fidelity))
    print(Order(ann, cart, fidelity))

    banana_cart = [
        LineItem('banana', 30, .5),
        LineItem('apple', 10, 1.5)
    ]

    print(Order(joe, banana_cart, bulk_item))

    long_order = [LineItem(str(item_code), 1, 1.0) for item_code in range(10)]
    print(Order(joe, long_order, large_order))
    print(Order(joe, cart, large_order))

    print(Order(joe, long_order, best_promo))
    print(Order(joe, banana_cart, best_promo))
    print(Order(ann, cart, best_promo))