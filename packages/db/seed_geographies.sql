-- Data Palestine — Geography Seed Data
-- 16 governorates + 2 territories + 1 national = 19 records
-- Codes aligned with PCBS P-codes and OCHA COD-AB boundaries
-- Note: This data is also embedded in schema.sql and runs automatically via Docker init.

INSERT INTO geographies (code, name_en, name_ar, level, parent_code) VALUES
    ('PS', 'Palestine', 'فلسطين', 'national', NULL),
    ('PS-WBK', 'West Bank', 'الضفة الغربية', 'territory', 'PS'),
    ('PS-GZA', 'Gaza Strip', 'قطاع غزة', 'territory', 'PS'),
    -- West Bank Governorates (11)
    ('PS-WBK-JEN', 'Jenin', 'جنين', 'governorate', 'PS-WBK'),
    ('PS-WBK-TBS', 'Tubas', 'طوباس', 'governorate', 'PS-WBK'),
    ('PS-WBK-TKM', 'Tulkarm', 'طولكرم', 'governorate', 'PS-WBK'),
    ('PS-WBK-NBS', 'Nablus', 'نابلس', 'governorate', 'PS-WBK'),
    ('PS-WBK-QQA', 'Qalqiliya', 'قلقيلية', 'governorate', 'PS-WBK'),
    ('PS-WBK-SLT', 'Salfit', 'سلفيت', 'governorate', 'PS-WBK'),
    ('PS-WBK-RBH', 'Ramallah & Al-Bireh', 'رام الله والبيرة', 'governorate', 'PS-WBK'),
    ('PS-WBK-JRH', 'Jericho & Al-Aghwar', 'أريحا والأغوار', 'governorate', 'PS-WBK'),
    ('PS-WBK-JEM', 'Jerusalem', 'القدس', 'governorate', 'PS-WBK'),
    ('PS-WBK-BTH', 'Bethlehem', 'بيت لحم', 'governorate', 'PS-WBK'),
    ('PS-WBK-HBN', 'Hebron', 'الخليل', 'governorate', 'PS-WBK'),
    -- Gaza Governorates (5)
    ('PS-GZA-NGZ', 'North Gaza', 'شمال غزة', 'governorate', 'PS-GZA'),
    ('PS-GZA-GZA', 'Gaza', 'غزة', 'governorate', 'PS-GZA'),
    ('PS-GZA-DEB', 'Deir Al-Balah', 'دير البلح', 'governorate', 'PS-GZA'),
    ('PS-GZA-KYS', 'Khan Yunis', 'خان يونس', 'governorate', 'PS-GZA'),
    ('PS-GZA-RFH', 'Rafah', 'رفح', 'governorate', 'PS-GZA')
ON CONFLICT (code) DO NOTHING;
