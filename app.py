<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>BusCar · Book Bus Tickets Online</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet" />
    <style>
        * { font-family: 'Inter', sans-serif; }
        body { background: #f0f4f8; }
        
        .hero-section {
            background: linear-gradient(145deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
            padding: 80px 20px 100px;
            text-align: center;
            color: white;
            position: relative;
            overflow: hidden;
        }
        .hero-section::before {
            content: '';
            position: absolute;
            inset: 0;
            background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' fill='none'/%3E%3Cpath d='M10 10 L90 10 L90 90 L10 90 Z' stroke='rgba(255,255,255,0.02)' stroke-width='1'/%3E%3C/svg%3E");
            pointer-events: none;
        }
        .hero-section h1 { font-size: 3.5rem; font-weight: 900; letter-spacing: -2px; margin-bottom: 12px; }
        .hero-section h1 span { color: #f59e0b; }
        .hero-section p { color: #94a3b8; max-width: 500px; margin: 0 auto 32px; font-size: 1.1rem; line-height: 1.7; }
        
        .search-card {
            background: white;
            border-radius: 24px;
            padding: 32px;
            max-width: 900px;
            margin: -60px auto 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.08);
            position: relative;
            z-index: 10;
        }
        .search-card .form-input {
            border: 1.5px solid #e2e8f0;
            border-radius: 14px;
            padding: 14px 16px;
            width: 100%;
            font-size: 0.95rem;
            transition: all 0.2s;
        }
        .search-card .form-input:focus {
            outline: none;
            border-color: #f59e0b;
            box-shadow: 0 0 0 4px rgba(245, 158, 11, 0.08);
        }
        .btn-primary {
            background: linear-gradient(135deg, #f59e0b, #d97706);
            color: white;
            padding: 14px 32px;
            border-radius: 9999px;
            font-weight: 700;
            border: none;
            cursor: pointer;
            transition: all 0.3s;
        }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(245, 158, 11, 0.35); }
        
        .section-title { font-size: 2rem; font-weight: 800; color: #0f172a; }
        .section-title span { color: #f59e0b; }
        
        .feature-card {
            background: white;
            border-radius: 20px;
            padding: 24px;
            text-align: center;
            border: 1px solid #f1f5f9;
            transition: all 0.3s;
        }
        .feature-card:hover { transform: translateY(-6px); box-shadow: 0 12px 30px rgba(0,0,0,0.04); }
        .feature-card i { color: #f59e0b; font-size: 2.5rem; display: block; margin-bottom: 12px; }
        .feature-card h4 { font-weight: 700; color: #0f172a; }
        .feature-card p { color: #64748b; font-size: 0.85rem; }
        
        .offer-card {
            background: linear-gradient(135deg, #f59e0b, #d97706);
            border-radius: 20px;
            padding: 24px;
            color: white;
            position: relative;
            overflow: hidden;
        }
        .offer-card::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -20%;
            width: 200px;
            height: 200px;
            background: rgba(255,255,255,0.05);
            border-radius: 50%;
        }
        .offer-card .offer-price { font-size: 2.5rem; font-weight: 900; }
        .offer-card .offer-desc { font-size: 0.9rem; opacity: 0.9; }
        
        .testimonial-card {
            background: white;
            border-radius: 20px;
            padding: 24px;
            border: 1px solid #f1f5f9;
        }
        .testimonial-card .stars { color: #f59e0b; margin-bottom: 8px; }
        .testimonial-card .quote { font-style: italic; color: #475569; line-height: 1.6; }
        .testimonial-card .author { display: flex; align-items: center; gap: 12px; margin-top: 12px; }
        .testimonial-card .author .avatar {
            width: 44px; height: 44px; border-radius: 50%;
            background: linear-gradient(135deg, #f59e0b, #d97706);
            display: flex; align-items: center; justify-content: center;
            color: white; font-weight: 700;
        }
        
        @media (max-width: 768px) {
            .hero-section h1 { font-size: 2.2rem; }
            .search-card { padding: 20px; margin-top: -40px; }
            .search-grid { grid-template-columns: 1fr !important; }
            .feature-grid { grid-template-columns: 1fr 1fr !important; }
            .offer-grid { grid-template-columns: 1fr !important; }
        }
    </style>
</head>
<body>

    <!-- ===== HEADER ===== -->
    <header style="background:white; padding:16px 20px; box-shadow:0 2px 10px rgba(0,0,0,0.04); position:sticky; top:0; z-index:50;">
        <div style="max-width:1200px; margin:0 auto; display:flex; align-items:center; justify-content:space-between;">
            <a href="/" style="display:flex; align-items:center; gap:10px; text-decoration:none; font-weight:800; font-size:1.3rem; color:#0f172a;">
                <i class="fas fa-bus" style="color:#f59e0b;"></i> Bus<span style="color:#f59e0b;">Car</span>
            </a>
            <div style="display:flex; align-items:center; gap:16px;">
                <a href="/check-booking" style="color:#64748b; text-decoration:none; font-weight:500; font-size:0.9rem;">
                    <i class="fas fa-ticket-alt"></i> Check Booking
                </a>
                <a href="/admin/login" style="color:#64748b; text-decoration:none; font-weight:500; font-size:0.9rem;">
                    <i class="fas fa-user-shield"></i> Admin
                </a>
            </div>
        </div>
    </header>

    <!-- ===== HERO ===== -->
    <section class="hero-section">
        <h1>Travel <span>Smart</span>, Travel <span>Safe</span></h1>
        <p>Book your bus tickets online with ease. Compare prices, choose your seats, and travel comfortably.</p>
    </section>

    <!-- ===== SEARCH CARD ===== -->
    <div class="search-card">
        <form action="/search" method="GET">
            <div class="search-grid" style="display:grid; grid-template-columns:1fr 1fr 1fr 1fr auto; gap:16px; align-items:end;">
                <div>
                    <label style="font-size:0.75rem; font-weight:600; color:#475569; display:block; margin-bottom:4px;">
                        <i class="fas fa-map-marker-alt" style="color:#f59e0b;"></i> From
                    </label>
                    <input type="text" name="origin" class="form-input" placeholder="Nairobi" required />
                </div>
                <div>
                    <label style="font-size:0.75rem; font-weight:600; color:#475569; display:block; margin-bottom:4px;">
                        <i class="fas fa-flag-checkered" style="color:#f59e0b;"></i> To
                    </label>
                    <input type="text" name="destination" class="form-input" placeholder="Mombasa" required />
                </div>
                <div>
                    <label style="font-size:0.75rem; font-weight:600; color:#475569; display:block; margin-bottom:4px;">
                        <i class="fas fa-calendar" style="color:#f59e0b;"></i> Date
                    </label>
                    <input type="date" name="date" class="form-input" required />
                </div>
                <div>
                    <label style="font-size:0.75rem; font-weight:600; color:#475569; display:block; margin-bottom:4px;">
                        <i class="fas fa-users" style="color:#f59e0b;"></i> Passengers
                    </label>
                    <input type="number" name="passengers" class="form-input" min="1" max="10" value="1" required />
                </div>
                <div>
                    <button type="submit" class="btn-primary" style="padding:14px 28px; width:100%;">
                        <i class="fas fa-search"></i> Search
                    </button>
                </div>
            </div>
        </form>
    </div>

    <!-- ===== FEATURES ===== -->
    <section style="max-width:1200px; margin:0 auto; padding:0 20px 40px;">
        <div style="text-align:center; margin-bottom:32px;">
            <h2 class="section-title">Why <span>BusCar</span></h2>
            <p style="color:#64748b; max-width:500px; margin:0 auto;">The smartest way to book bus tickets online</p>
        </div>
        <div class="feature-grid" style="display:grid; grid-template-columns:repeat(4,1fr); gap:20px;">
            <div class="feature-card">
                <i class="fas fa-shield-alt"></i>
                <h4>Safe Travel</h4>
                <p>Verified buses with safety standards</p>
            </div>
            <div class="feature-card">
                <i class="fas fa-chair"></i>
                <h4>Choose Seats</h4>
                <p>Pick your preferred seat location</p>
            </div>
            <div class="feature-card">
                <i class="fas fa-tag"></i>
                <h4>Best Prices</h4>
                <p>Compare and save on your trip</p>
            </div>
            <div class="feature-card">
                <i class="fas fa-headset"></i>
                <h4>24/7 Support</h4>
                <p>We're here to help anytime</p>
            </div>
        </div>
    </section>

    <!-- ===== OFFERS ===== -->
    <section style="max-width:1200px; margin:0 auto; padding:0 20px 40px;">
        <div style="text-align:center; margin-bottom:32px;">
            <h2 class="section-title">Special <span>Offers</span></h2>
            <p style="color:#64748b;">Grab these deals before they're gone</p>
        </div>
        <div class="offer-grid" style="display:grid; grid-template-columns:repeat(2,1fr); gap:20px;">
            <div class="offer-card">
                <div class="offer-price">KSh 500</div>
                <div class="offer-desc">Nairobi → Kisumu</div>
                <div style="font-size:0.8rem; opacity:0.8;">Limited seats available</div>
            </div>
            <div class="offer-card" style="background:linear-gradient(135deg, #3b82f6, #1d4ed8);">
                <div class="offer-price">KSh 800</div>
                <div class="offer-desc">Nairobi → Mombasa</div>
                <div style="font-size:0.8rem; opacity:0.8;">Executive class</div>
            </div>
        </div>
    </section>

    <!-- ===== TESTIMONIALS ===== -->
    <section style="max-width:1200px; margin:0 auto; padding:0 20px 40px;">
        <div style="text-align:center; margin-bottom:32px;">
            <h2 class="section-title">What Our <span>Customers</span> Say</h2>
        </div>
        <div style="display:grid; grid-template-columns:repeat(3,1fr); gap:20px;">
            <div class="testimonial-card">
                <div class="stars"><i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star"></i></div>
                <div class="quote">"BusCar made booking my trip so easy. The seat selection was great!"</div>
                <div class="author">
                    <div class="avatar">JM</div>
                    <div><strong>James Mwangi</strong><br><span style="font-size:0.75rem; color:#94a3b8;">Nairobi → Mombasa</span></div>
                </div>
            </div>
            <div class="testimonial-card">
                <div class="stars"><i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star"></i></div>
                <div class="quote">"Best bus booking platform in Kenya. Fast, reliable, and affordable."</div>
                <div class="author">
                    <div class="avatar">SO</div>
                    <div><strong>Sarah Ochieng</strong><br><span style="font-size:0.75rem; color:#94a3b8;">Kisumu → Nairobi</span></div>
                </div>
            </div>
            <div class="testimonial-card">
                <div class="stars"><i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star"></i><i class="fas fa-star"></i></div>
                <div class="quote">"I love the real-time seat availability. Highly recommend BusCar!"</div>
                <div class="author">
                    <div class="avatar">DK</div>
                    <div><strong>David Kiprop</strong><br><span style="font-size:0.75rem; color:#94a3b8;">Eldoret → Nairobi</span></div>
                </div>
            </div>
        </div>
    </section>

    <!-- ===== FOOTER ===== -->
    <footer style="background:white; padding:24px 20px; text-align:center; border-top:1px solid #f1f5f9;">
        <p style="color:#94a3b8; font-size:0.85rem;">© 2026 BusCar. All rights reserved.</p>
        <p style="color:#cbd5e1; font-size:0.75rem; margin-top:4px;">
            <i class="fas fa-lock" style="color:#f59e0b;"></i> Secure booking
        </p>
    </footer>

    <script>
        // Set min date to today
        document.addEventListener('DOMContentLoaded', function() {
            const dateInput = document.querySelector('input[name="date"]');
            if (dateInput) {
                const today = new Date().toISOString().split('T')[0];
                dateInput.setAttribute('min', today);
            }
        });
    </script>
</body>
</html>
