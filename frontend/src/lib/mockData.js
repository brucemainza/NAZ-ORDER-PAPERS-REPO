// Temporary datasets for the two administration screens whose write APIs are
// not implemented yet. Operational submission and search flows use the API.
export const mockSessions = [
    {
        id: "session-13-2022",
        name: "Thirteenth National Assembly - First Session",
        startDate: "2022-09-16",
        endDate: "2023-08-11",
        status: "Closed",
    },
    {
        id: "session-13-2023",
        name: "Thirteenth National Assembly - Second Session",
        startDate: "2023-09-08",
        endDate: "2024-08-09",
        status: "Closed",
    },
    {
        id: "session-13-2024",
        name: "Thirteenth National Assembly - Third Session",
        startDate: "2024-09-13",
        endDate: "2025-08-08",
        status: "Closed",
    },
    {
        id: "session-13-2025",
        name: "Thirteenth National Assembly - Fourth Session",
        startDate: "2025-09-12",
        endDate: "2026-08-14",
        status: "Active",
    },
    {
        id: "session-13-2026",
        name: "Thirteenth National Assembly - Fifth Session",
        startDate: "2026-09-11",
        endDate: "2027-08-13",
        status: "Upcoming",
    },
];

export const mockUsers = [
    {
        id: "user-1",
        name: "Lilian Mwape",
        employeeId: "EMP-001",
        role: "Admin",
        status: "Active",
        lastLogin: "2026-04-28T07:42:00.000Z",
    },
    {
        id: "user-2",
        name: "Patrick Zulu",
        employeeId: "EMP-002",
        role: "Admin",
        status: "Active",
        lastLogin: "2026-04-28T06:58:00.000Z",
    },
    {
        id: "user-3",
        name: "Naomi Chisanga",
        employeeId: "EMP-003",
        role: "Senior Clerk",
        status: "Active",
        lastLogin: "2026-04-27T15:16:00.000Z",
    },
    {
        id: "user-4",
        name: "Brian Musonda",
        employeeId: "EMP-004",
        role: "Clerk",
        status: "Active",
        lastLogin: "2026-04-27T12:31:00.000Z",
    },
    {
        id: "user-5",
        name: "Mercy Siame",
        employeeId: "EMP-005",
        role: "Clerk",
        status: "Inactive",
        lastLogin: "2026-04-21T09:05:00.000Z",
    },
];
