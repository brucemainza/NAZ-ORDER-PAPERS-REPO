-- Configurable permissions and roles
INSERT INTO permissions (code, description)
VALUES
  ('submit_question', 'Submit questions for oral or written answer'),
  ('submit_motion', 'Submit notices of motion'),
  ('review_submission', 'Review submitted questions and motions'),
  ('approve_motion', 'Approve a submission after review'),
  ('reject_submission', 'Reject a submission after review'),
  ('request_changes', 'Return a submission to its owner for changes'),
  ('schedule_item', 'Schedule an approved item for a sitting'),
  ('record_response', 'Record the House response to a scheduled question'),
  ('view_reports', 'View operational reports'),
  ('view_audit', 'View the system audit trail'),
  ('manage_users', 'Manage user accounts and account locks'),
  ('manage_roles', 'Manage roles and permission assignments'),
  ('manage_sessions', 'Manage parliamentary sessions'),
  ('search_archive', 'Search archived parliamentary records'),
  ('view_archive', 'View archived parliamentary records')
ON CONFLICT (code) DO UPDATE SET description = EXCLUDED.description;

INSERT INTO roles (name, description)
VALUES
  ('Administrator', 'Full system administration'),
  ('Clerk', 'Submission review and parliamentary scheduling'),
  ('Member of Parliament', 'Question and motion submission'),
  ('Viewer', 'Read-only reporting and archive access')
ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON (
  r.name = 'Administrator'
  OR (r.name = 'Clerk' AND p.code IN (
    'review_submission', 'approve_motion', 'reject_submission',
    'request_changes', 'schedule_item', 'record_response', 'view_reports', 'view_audit',
    'manage_sessions', 'search_archive', 'view_archive'
  ))
  OR (r.name = 'Member of Parliament' AND p.code IN (
    'submit_question', 'submit_motion', 'view_reports',
    'search_archive', 'view_archive'
  ))
  OR (r.name = 'Viewer' AND p.code IN (
    'view_reports', 'search_archive', 'view_archive'
  ))
)
ON CONFLICT DO NOTHING;

-- Users
INSERT INTO users (employee_id, name, role, status, password_hash)
VALUES
  ('EMP-001', 'Lilian Mwape', 'Admin', 'Active', '$2b$12$PkG3pUy6HoFHjU3OosNV/On2RKoKx7ZLNnWyvX7A5WgIWR3ydwCBq'),
  ('EMP-002', 'Patrick Zulu', 'Admin', 'Active', '$2b$12$PkG3pUy6HoFHjU3OosNV/On2RKoKx7ZLNnWyvX7A5WgIWR3ydwCBq'),
  ('EMP-003', 'Naomi Chisanga', 'Senior Clerk', 'Active', '$2b$12$PkG3pUy6HoFHjU3OosNV/On2RKoKx7ZLNnWyvX7A5WgIWR3ydwCBq'),
  ('EMP-004', 'Brian Musonda', 'Clerk', 'Active', '$2b$12$PkG3pUy6HoFHjU3OosNV/On2RKoKx7ZLNnWyvX7A5WgIWR3ydwCBq'),
  ('EMP-005', 'Mercy Siame', 'Clerk', 'Inactive', '$2b$12$PkG3pUy6HoFHjU3OosNV/On2RKoKx7ZLNnWyvX7A5WgIWR3ydwCBq')
ON CONFLICT (employee_id) DO NOTHING;

INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id
FROM users u
JOIN roles r ON r.name = CASE
  WHEN u.role = 'Admin' THEN 'Administrator'
  WHEN u.role IN ('Senior Clerk', 'Clerk') THEN 'Clerk'
END
WHERE NOT EXISTS (
  SELECT 1 FROM user_roles ur WHERE ur.user_id = u.id
)
ON CONFLICT DO NOTHING;

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
  'To ask the Minister of Health whether the Government has any plans to increase qualified staffing levels at rural health posts in Luapula Province where persistent vacancies continue to affect service delivery.', 'Archived'
FROM parliamentary_sessions s WHERE s.code = 'session-13-2025'
AND NOT EXISTS (SELECT 1 FROM parliamentary_records r WHERE r.subject = 'Rural Health Post Staffing Levels');

INSERT INTO parliamentary_records (item_type, session_id, member, ministry, subject, full_text, status)
SELECT 'Question', s.id, 'Hon. Mutale Nalumango', 'Ministry of Education', 'Teacher Deployment in Newly Opened Schools',
  'To ask the Minister of Education when the Ministry will complete teacher deployment to newly opened secondary schools in Northern Province and what interim staffing arrangements are in place.', 'Archived'
FROM parliamentary_sessions s WHERE s.code = 'session-13-2025'
AND NOT EXISTS (SELECT 1 FROM parliamentary_records r WHERE r.subject = 'Teacher Deployment in Newly Opened Schools');

INSERT INTO parliamentary_records (item_type, session_id, member, ministry, subject, full_text, status)
SELECT 'Motion', s.id, 'Hon. Miriam Chonya', NULL, 'Motion on Strengthening Constituency Information Desks',
  'That this House urges the Government to standardise constituency information desks and ensure every district office provides timely public access to parliamentary notices and explanatory briefs.', 'Archived'
FROM parliamentary_sessions s WHERE s.code = 'session-13-2024'
AND NOT EXISTS (SELECT 1 FROM parliamentary_records r WHERE r.subject = 'Motion on Strengthening Constituency Information Desks');

INSERT INTO parliamentary_records (item_type, session_id, member, ministry, subject, full_text, status)
SELECT 'Question', s.id, 'Hon. Given Katuta', 'Ministry of Local Government and Rural Development', 'Community Water Point Rehabilitation',
  'To ask the Minister of Local Government and Rural Development how many community water points were rehabilitated in Kasama District between January and September 2025 and what budget line financed the works.', 'Archived'
FROM parliamentary_sessions s WHERE s.code = 'session-13-2024'
AND NOT EXISTS (SELECT 1 FROM parliamentary_records r WHERE r.subject = 'Community Water Point Rehabilitation');

INSERT INTO parliamentary_records (item_type, session_id, member, ministry, subject, full_text, status)
SELECT 'Motion', s.id, 'Hon. Sydney Mushanga', NULL, 'Motion on Digital Archiving of Committee Reports',
  'That this House resolves that all committee reports tabled before the House be digitised and indexed through a central archival system for institutional continuity and research access.', 'Archived'
FROM parliamentary_sessions s WHERE s.code = 'session-13-2023'
AND NOT EXISTS (SELECT 1 FROM parliamentary_records r WHERE r.subject = 'Motion on Digital Archiving of Committee Reports');
