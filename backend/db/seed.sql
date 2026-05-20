-- Users
INSERT INTO users (employee_id, name, role, status, password_hash)
VALUES
  ('EMP-001', 'Lilian Mwape', 'Admin', 'Active', '$2b$12$PkG3pUy6HoFHjU3OosNV/On2RKoKx7ZLNnWyvX7A5WgIWR3ydwCBq'),
  ('EMP-002', 'Patrick Zulu', 'Admin', 'Active', '$2b$12$PkG3pUy6HoFHjU3OosNV/On2RKoKx7ZLNnWyvX7A5WgIWR3ydwCBq'),
  ('EMP-003', 'Naomi Chisanga', 'Senior Clerk', 'Active', '$2b$12$PkG3pUy6HoFHjU3OosNV/On2RKoKx7ZLNnWyvX7A5WgIWR3ydwCBq'),
  ('EMP-004', 'Brian Musonda', 'Clerk', 'Active', '$2b$12$PkG3pUy6HoFHjU3OosNV/On2RKoKx7ZLNnWyvX7A5WgIWR3ydwCBq'),
  ('EMP-005', 'Mercy Siame', 'Clerk', 'Inactive', '$2b$12$PkG3pUy6HoFHjU3OosNV/On2RKoKx7ZLNnWyvX7A5WgIWR3ydwCBq')
ON CONFLICT (employee_id) DO NOTHING;

-- Parliamentary Sessions
INSERT INTO parliamentary_sessions (code, name, start_date, end_date, status)
VALUES
  ('session-13-2022', 'Thirteenth National Assembly - First Session', '2022-09-16', '2023-08-11', 'Closed'),
  ('session-13-2023', 'Thirteenth National Assembly - Second Session', '2023-09-08', '2024-08-09', 'Closed'),
  ('session-13-2024', 'Thirteenth National Assembly - Third Session', '2024-09-13', '2025-08-08', 'Closed'),
  ('session-13-2025', 'Thirteenth National Assembly - Fourth Session', '2025-09-12', '2026-08-14', 'Active'),
  ('session-13-2026', 'Thirteenth National Assembly - Fifth Session', '2026-09-11', '2027-08-13', 'Upcoming')
ON CONFLICT (code) DO NOTHING;

-- Parliamentary Records (Questions and Motions)
INSERT INTO parliamentary_records (item_type, session_id, member, ministry, subject, full_text, status)
SELECT 'Question', s.id, 'Hon. Chanda Katotobwe', 'Ministry of Health', 'Rural Health Post Staffing Levels',
  'To ask the Minister of Health whether the Government has any plans to increase qualified staffing levels at rural health posts in Luapula Province where persistent vacancies continue to affect service delivery.', 'Historical'
FROM parliamentary_sessions s WHERE s.code = 'session-13-2025'
AND NOT EXISTS (SELECT 1 FROM parliamentary_records r WHERE r.subject = 'Rural Health Post Staffing Levels');

INSERT INTO parliamentary_records (item_type, session_id, member, ministry, subject, full_text, status)
SELECT 'Question', s.id, 'Hon. Mutale Nalumango', 'Ministry of Education', 'Teacher Deployment in Newly Opened Schools',
  'To ask the Minister of Education when the Ministry will complete teacher deployment to newly opened secondary schools in Northern Province and what interim staffing arrangements are in place.', 'Historical'
FROM parliamentary_sessions s WHERE s.code = 'session-13-2025'
AND NOT EXISTS (SELECT 1 FROM parliamentary_records r WHERE r.subject = 'Teacher Deployment in Newly Opened Schools');

INSERT INTO parliamentary_records (item_type, session_id, member, ministry, subject, full_text, status)
SELECT 'Motion', s.id, 'Hon. Miriam Chonya', NULL, 'Motion on Strengthening Constituency Information Desks',
  'That this House urges the Government to standardise constituency information desks and ensure every district office provides timely public access to parliamentary notices and explanatory briefs.', 'Historical'
FROM parliamentary_sessions s WHERE s.code = 'session-13-2024'
AND NOT EXISTS (SELECT 1 FROM parliamentary_records r WHERE r.subject = 'Motion on Strengthening Constituency Information Desks');

INSERT INTO parliamentary_records (item_type, session_id, member, ministry, subject, full_text, status)
SELECT 'Question', s.id, 'Hon. Given Katuta', 'Ministry of Local Government and Rural Development', 'Community Water Point Rehabilitation',
  'To ask the Minister of Local Government and Rural Development how many community water points were rehabilitated in Kasama District between January and September 2025 and what budget line financed the works.', 'Historical'
FROM parliamentary_sessions s WHERE s.code = 'session-13-2024'
AND NOT EXISTS (SELECT 1 FROM parliamentary_records r WHERE r.subject = 'Community Water Point Rehabilitation');

INSERT INTO parliamentary_records (item_type, session_id, member, ministry, subject, full_text, status)
SELECT 'Motion', s.id, 'Hon. Sydney Mushanga', NULL, 'Motion on Digital Archiving of Committee Reports',
  'That this House resolves that all committee reports tabled before the House be digitised and indexed through a central archival system for institutional continuity and research access.', 'Historical'
FROM parliamentary_sessions s WHERE s.code = 'session-13-2023'
AND NOT EXISTS (SELECT 1 FROM parliamentary_records r WHERE r.subject = 'Motion on Digital Archiving of Committee Reports');