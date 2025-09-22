-- Medical Waste Classification Database Initialization
CREATE TABLE IF NOT EXISTS classifications (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    classification VARCHAR(50) NOT NULL,
    item_name VARCHAR(200),
    confidence DECIMAL(5,4),
    image_path VARCHAR(500)
);

CREATE TABLE IF NOT EXISTS bin_levels (
    id SERIAL PRIMARY KEY,
    bin_type VARCHAR(50) NOT NULL,
    fill_percentage INTEGER CHECK (fill_percentage >= 0 AND fill_percentage <= 100),
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO bin_levels (bin_type, fill_percentage) VALUES 
('General-Biomedical', 25),
('Infectious', 45),
('Sharp', 10),
('Pharmaceutical', 60)
ON CONFLICT DO NOTHING;