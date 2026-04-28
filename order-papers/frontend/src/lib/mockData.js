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
export const mockSubmissions = [
    {
        id: "sub-001",
        type: "Question",
        sessionId: "session-13-2025",
        member: "Hon. Chanda Katotobwe",
        ministry: "Ministry of Health",
        subject: "Rural Health Post Staffing Levels",
        fullText: "To ask the Minister of Health whether the Government has any plans to increase qualified staffing levels at rural health posts in Luapula Province where persistent vacancies continue to affect service delivery.",
        submittedBy: "Naomi Chisanga",
        submittedAt: "2026-04-25T08:00:00.000Z",
        status: "Pending",
    },
    {
        id: "sub-002",
        type: "Question",
        sessionId: "session-13-2025",
        member: "Hon. Mutale Nalumango",
        ministry: "Ministry of Education",
        subject: "Teacher Deployment in Newly Opened Schools",
        fullText: "To ask the Minister of Education when the Ministry will complete teacher deployment to newly opened secondary schools in Northern Province and what interim staffing arrangements are in place.",
        submittedBy: "Brian Musonda",
        submittedAt: "2026-04-24T10:15:00.000Z",
        status: "Pending",
    },
    {
        id: "sub-003",
        type: "Motion",
        sessionId: "session-13-2024",
        member: "Hon. Miriam Chonya",
        subject: "Motion on Strengthening Constituency Information Desks",
        fullText: "That this House urges the Government to standardise constituency information desks and ensure every district office provides timely public access to parliamentary notices and explanatory briefs.",
        submittedBy: "Lilian Mwape",
        submittedAt: "2025-11-14T09:30:00.000Z",
        status: "Reviewed",
    },
    {
        id: "sub-004",
        type: "Question",
        sessionId: "session-13-2024",
        member: "Hon. Given Katuta",
        ministry: "Ministry of Local Government and Rural Development",
        subject: "Community Water Point Rehabilitation",
        fullText: "To ask the Minister of Local Government and Rural Development how many community water points were rehabilitated in Kasama District between January and September 2025 and what budget line financed the works.",
        submittedBy: "Patrick Zulu",
        submittedAt: "2025-10-03T11:40:00.000Z",
        status: "Clear",
    },
    {
        id: "sub-005",
        type: "Motion",
        sessionId: "session-13-2023",
        member: "Hon. Sydney Mushanga",
        subject: "Motion on Digital Archiving of Committee Reports",
        fullText: "That this House resolves that all committee reports tabled before the House be digitised and indexed through a central archival system for institutional continuity and research access.",
        submittedBy: "Naomi Chisanga",
        submittedAt: "2024-03-18T13:00:00.000Z",
        status: "Reviewed",
    },
    {
        id: "sub-006",
        type: "Question",
        sessionId: "session-13-2023",
        member: "Hon. Kapembwa Simbao",
        ministry: "Ministry of Transport and Logistics",
        subject: "Bridge Maintenance on Feeder Roads",
        fullText: "To ask the Minister of Transport and Logistics what measures the Government has taken to maintain small-span bridges on feeder roads in flood-prone constituencies and how contracts are supervised.",
        submittedBy: "Mercy Siame",
        submittedAt: "2024-04-02T07:55:00.000Z",
        status: "Duplicate",
    },
    {
        id: "sub-007",
        type: "Question",
        sessionId: "session-13-2022",
        member: "Hon. Stephen Kampyongo",
        ministry: "Ministry of Home Affairs and Internal Security",
        subject: "Police Housing Upgrades",
        fullText: "To ask the Minister of Home Affairs and Internal Security how many police housing units were rehabilitated in 2023 and what criteria were used to prioritise locations.",
        submittedBy: "Brian Musonda",
        submittedAt: "2023-06-09T08:20:00.000Z",
        status: "Clear",
    },
    {
        id: "sub-008",
        type: "Motion",
        sessionId: "session-13-2025",
        member: "Hon. Maureen Mabonga",
        subject: "Motion on Service Charters for Provincial Offices",
        fullText: "That this House recommends that all provincial ministerial offices publish updated service charters displaying processing timelines, contact details and escalation routes for citizens.",
        submittedBy: "Patrick Zulu",
        submittedAt: "2026-03-29T14:45:00.000Z",
        status: "Pending",
    },
    {
        id: "sub-009",
        type: "Question",
        sessionId: "session-13-2025",
        member: "Hon. Milupi Mwelwa",
        ministry: "Ministry of Agriculture",
        subject: "Fertiliser Distribution Delays",
        fullText: "To ask the Minister of Agriculture what caused late fertiliser deliveries under the input support programme in selected wards of Western Province during the 2025 farming season.",
        submittedBy: "Lilian Mwape",
        submittedAt: "2026-02-20T10:05:00.000Z",
        status: "Pending",
    },
    {
        id: "sub-010",
        type: "Motion",
        sessionId: "session-13-2024",
        member: "Hon. Brenda Nyirenda",
        subject: "Motion on Publishing Annual Question Response Timelines",
        fullText: "That this House directs the relevant parliamentary departments to publish annual statistics on average turnaround times for written and oral responses from ministries.",
        submittedBy: "Naomi Chisanga",
        submittedAt: "2025-12-01T12:10:00.000Z",
        status: "Reviewed",
    },
];
export const mockSimilarityResults = [
    {
        id: "match-001",
        sourceSubmissionId: "sub-011",
        title: "Health Staffing at Rural Posts",
        score: 91,
        sessionId: "session-13-2024",
        member: "Hon. Chola Banda",
        ministry: "Ministry of Health",
        date: "2025-10-12T09:00:00.000Z",
        itemType: "Question",
        snippet: "A prior question asked whether the Government had plans to increase staffing at rural health posts experiencing long-standing vacancies.",
        fullText: "To ask the Minister of Health whether there are immediate plans to recruit and deploy additional clinical staff to rural health posts that have operated below establishment for more than twelve months.",
    },
    {
        id: "match-002",
        sourceSubmissionId: "sub-012",
        title: "Teacher Deployment to New Schools",
        score: 88,
        sessionId: "session-13-2025",
        member: "Hon. Doreen Mwamba",
        ministry: "Ministry of Education",
        date: "2026-02-18T10:25:00.000Z",
        itemType: "Question",
        snippet: "This question examined staffing timelines for newly commissioned secondary schools pending teacher placement.",
        fullText: "To ask the Minister of Education by what date the Ministry expects to complete teacher deployment to newly commissioned schools in remote districts and what stop-gap interventions are being used.",
    },
    {
        id: "match-003",
        sourceSubmissionId: "sub-013",
        title: "Constituency Information Desk Standards",
        score: 76,
        sessionId: "session-13-2023",
        member: "Hon. George Chisanga",
        date: "2024-05-09T14:10:00.000Z",
        itemType: "Motion",
        snippet: "A motion proposed common operating standards for constituency information desks and public notices.",
        fullText: "That this House urges the Executive to adopt minimum operating standards for constituency information desks, including public notice displays, visitor logs and service turnaround guidelines.",
    },
    {
        id: "match-004",
        sourceSubmissionId: "sub-014",
        title: "Water Point Maintenance Inventory",
        score: 63,
        sessionId: "session-13-2024",
        member: "Hon. Fred Chaatila",
        ministry: "Ministry of Local Government and Rural Development",
        date: "2025-09-18T08:40:00.000Z",
        itemType: "Question",
        snippet: "Historical record covering rehabilitated water points and district-level implementation reporting.",
        fullText: "To ask the Minister of Local Government and Rural Development how many communal water points were repaired in targeted districts and whether the Ministry maintains a district-by-district inventory.",
    },
    {
        id: "match-005",
        sourceSubmissionId: "sub-015",
        title: "Digital Archiving of Parliamentary Records",
        score: 84,
        sessionId: "session-13-2023",
        member: "Hon. Emeldah Munashabantu",
        date: "2024-03-02T11:00:00.000Z",
        itemType: "Motion",
        snippet: "A related motion sought the digitisation and indexing of committee records for archival continuity.",
        fullText: "That this House resolves that committee reports and associated explanatory memoranda be digitised, indexed and preserved within a searchable parliamentary archive.",
    },
    {
        id: "match-006",
        sourceSubmissionId: "sub-016",
        title: "Bridge Works Oversight in Flood Zones",
        score: 58,
        sessionId: "session-13-2022",
        member: "Hon. Malungo Chisangano",
        ministry: "Ministry of Transport and Logistics",
        date: "2023-07-11T07:20:00.000Z",
        itemType: "Question",
        snippet: "Previous oversight question on bridge maintenance contracts and supervision in flood-affected areas.",
        fullText: "To ask the Minister of Transport and Logistics what framework is used to supervise bridge maintenance contracts in flood-prone rural areas and how site quality is certified.",
    },
    {
        id: "match-007",
        sourceSubmissionId: "sub-017",
        title: "Police Housing Rehabilitation Update",
        score: 47,
        sessionId: "session-13-2022",
        member: "Hon. Peter Phiri",
        ministry: "Ministry of Home Affairs and Internal Security",
        date: "2023-05-30T09:55:00.000Z",
        itemType: "Question",
        snippet: "Older question seeking figures on rehabilitation works for police housing stock.",
        fullText: "To ask the Minister of Home Affairs and Internal Security for an update on police housing rehabilitation works and the basis used to identify sites for urgent attention.",
    },
    {
        id: "match-008",
        sourceSubmissionId: "sub-018",
        title: "Provincial Service Charter Publication",
        score: 81,
        sessionId: "session-13-2025",
        member: "Hon. Catherine Namugala",
        date: "2026-01-22T13:35:00.000Z",
        itemType: "Motion",
        snippet: "A motion recommending that provincial offices publish service standards and escalation contacts for public use.",
        fullText: "That this House recommends that provincial ministerial offices publish current service charters showing service timelines, public contacts and complaint escalation pathways.",
    },
];
export const mockDecisionHistory = [
    {
        id: "decision-1",
        submissionId: "sub-006",
        decision: "Duplicate",
        notes: "Substantially overlaps with prior feeder road oversight question tabled in the preceding session.",
        decidedBy: "Lilian Mwape",
        decidedAt: "2024-04-05T10:20:00.000Z",
    },
    {
        id: "decision-2",
        submissionId: "sub-003",
        decision: "Substantially Similar",
        notes: "May proceed after narrowing the administrative implementation scope.",
        decidedBy: "Patrick Zulu",
        decidedAt: "2025-11-15T09:10:00.000Z",
    },
    {
        id: "decision-3",
        submissionId: "sub-004",
        decision: "Clear (New)",
        notes: "No materially identical district data request found.",
        decidedBy: "Naomi Chisanga",
        decidedAt: "2025-10-04T08:50:00.000Z",
    },
];
export const mockAuditLogs = [
    { id: "audit-001", date: "2026-04-28T07:40:00.000Z", user: "Lilian Mwape", action: "Logged in", itemReference: "AUTH-LOGIN", ipAddress: "10.24.1.10" },
    { id: "audit-002", date: "2026-04-28T07:12:00.000Z", user: "Brian Musonda", action: "Submitted question", itemReference: "sub-002", ipAddress: "10.24.1.44" },
    { id: "audit-003", date: "2026-04-28T06:58:00.000Z", user: "Patrick Zulu", action: "Viewed audit report", itemReference: "REPORT-AUDIT", ipAddress: "10.24.1.18" },
    { id: "audit-004", date: "2026-04-27T15:20:00.000Z", user: "Naomi Chisanga", action: "Recorded similarity decision", itemReference: "sub-003", ipAddress: "10.24.1.32" },
    { id: "audit-005", date: "2026-04-27T14:40:00.000Z", user: "Lilian Mwape", action: "Added parliamentary session", itemReference: "session-13-2026", ipAddress: "10.24.1.10" },
    { id: "audit-006", date: "2026-04-27T12:34:00.000Z", user: "Brian Musonda", action: "Submitted motion", itemReference: "sub-008", ipAddress: "10.24.1.44" },
    { id: "audit-007", date: "2026-04-27T10:22:00.000Z", user: "Patrick Zulu", action: "Invited user", itemReference: "EMP-005", ipAddress: "10.24.1.18" },
    { id: "audit-008", date: "2026-04-26T16:05:00.000Z", user: "Naomi Chisanga", action: "Searched historical records", itemReference: "SEARCH-4812", ipAddress: "10.24.1.32" },
    { id: "audit-009", date: "2026-04-26T13:15:00.000Z", user: "Lilian Mwape", action: "Updated user role", itemReference: "EMP-004", ipAddress: "10.24.1.10" },
    { id: "audit-010", date: "2026-04-25T15:45:00.000Z", user: "Brian Musonda", action: "Viewed result record", itemReference: "sub-001", ipAddress: "10.24.1.44" },
    { id: "audit-011", date: "2026-04-25T14:08:00.000Z", user: "Patrick Zulu", action: "Exported CSV", itemReference: "AUDIT-EXPORT", ipAddress: "10.24.1.18" },
    { id: "audit-012", date: "2026-04-24T11:20:00.000Z", user: "Naomi Chisanga", action: "Submitted question", itemReference: "sub-001", ipAddress: "10.24.1.32" },
    { id: "audit-013", date: "2026-04-24T09:50:00.000Z", user: "Lilian Mwape", action: "Reviewed duplicate match", itemReference: "sub-006", ipAddress: "10.24.1.10" },
    { id: "audit-014", date: "2026-04-23T08:30:00.000Z", user: "Patrick Zulu", action: "Logged out", itemReference: "AUTH-LOGOUT", ipAddress: "10.24.1.18" },
    { id: "audit-015", date: "2026-04-22T12:10:00.000Z", user: "Naomi Chisanga", action: "Viewed reports dashboard", itemReference: "REPORTS", ipAddress: "10.24.1.32" },
];
function normalise(value) {
    return value
        .toLowerCase()
        .replace(/[^a-z0-9\s]/g, " ")
        .split(/\s+/)
        .filter((token) => token.length > 2);
}
function overlapScore(query, candidate) {
    const queryTokens = new Set(normalise(query));
    const candidateTokens = new Set(normalise(candidate));
    if (queryTokens.size === 0 || candidateTokens.size === 0) {
        return 0;
    }
    let matches = 0;
    queryTokens.forEach((token) => {
        if (candidateTokens.has(token)) {
            matches += 1;
        }
    });
    return matches / queryTokens.size;
}
function rankMatches(matches, query, sessionId, itemType) {
    const ranked = matches
        .filter((item) => (sessionId ? item.sessionId === sessionId : true))
        .filter((item) => (itemType && itemType !== "All" ? item.itemType === itemType : true))
        .map((item) => {
        const scoreBoost = Math.round(overlapScore(query, `${item.title} ${item.snippet} ${item.fullText}`) * 18);
        const sessionBoost = sessionId && item.sessionId === sessionId ? 4 : 0;
        const typeBoost = itemType && itemType !== "All" && item.itemType === itemType ? 4 : 0;
        return {
            ...item,
            score: Math.min(98, item.score + scoreBoost + sessionBoost + typeBoost),
        };
    })
        .sort((left, right) => right.score - left.score);
    return ranked.map((match, index) => ({ rank: index + 1, match }));
}
export function getSessionById(sessionId) {
    return mockSessions.find((session) => session.id === sessionId);
}
export function getSubmissionById(submissionId) {
    return mockSubmissions.find((submission) => submission.id === submissionId);
}
export function getDecisionHistory(submissionId) {
    return mockDecisionHistory.filter((entry) => entry.submissionId === submissionId);
}
export function getAuditTrailForItem(itemReference) {
    return mockAuditLogs.filter((entry) => entry.itemReference === itemReference);
}
export function searchHistoricalRecords(search) {
    const query = search.query.trim();
    if (!query && !search.sessionId && (!search.itemType || search.itemType === "All")) {
        return [];
    }
    const textFiltered = query
        ? mockSimilarityResults.filter((item) => {
            var _a;
            const haystack = `${item.title} ${item.snippet} ${item.fullText} ${item.member} ${(_a = item.ministry) !== null && _a !== void 0 ? _a : ""}`.toLowerCase();
            return haystack.includes(query.toLowerCase());
        })
        : mockSimilarityResults;
    const candidateMatches = textFiltered.length > 0 ? textFiltered : mockSimilarityResults;
    return rankMatches(candidateMatches, query, search.sessionId, search.itemType);
}
export function buildSimilarityResultsForSubmission(submission) {
    const query = [submission.subject, submission.fullText, submission.member, submission.ministry].filter(Boolean).join(" ");
    return rankMatches(mockSimilarityResults, query, submission.sessionId, submission.type).slice(0, 6);
}
