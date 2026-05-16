INSERT INTO users (employee_id, name, role, status, password_hash)
VALUES
  ('EMP-001', 'Lilian Mwape', 'Admin', 'Active', '$2b$12$PkG3pUy6HoFHjU3OosNV/On2RKoKx7ZLNnWyvX7A5WgIWR3ydwCBq'),
  ('EMP-002', 'Patrick Zulu', 'Admin', 'Active', '$2b$12$PkG3pUy6HoFHjU3OosNV/On2RKoKx7ZLNnWyvX7A5WgIWR3ydwCBq'),
  ('EMP-003', 'Naomi Chisanga', 'Senior Clerk', 'Active', '$2b$12$PkG3pUy6HoFHjU3OosNV/On2RKoKx7ZLNnWyvX7A5WgIWR3ydwCBq'),
  ('EMP-004', 'Brian Musonda', 'Clerk', 'Active', '$2b$12$PkG3pUy6HoFHjU3OosNV/On2RKoKx7ZLNnWyvX7A5WgIWR3ydwCBq'),
  ('EMP-005', 'Mercy Siame', 'Clerk', 'Inactive', '$2b$12$PkG3pUy6HoFHjU3OosNV/On2RKoKx7ZLNnWyvX7A5WgIWR3ydwCBq')
ON CONFLICT (employee_id) DO NOTHING;