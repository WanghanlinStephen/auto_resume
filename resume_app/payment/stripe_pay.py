import stripe

stripe.api_key = "你的 Stripe API Key"

def process_stripe_payment(charge_id, amount):
    charge = stripe.Charge.create(
        amount=int(amount * 100),
        currency="usd",
        description="订单支付",
        source=charge_id
    )
    return charge
