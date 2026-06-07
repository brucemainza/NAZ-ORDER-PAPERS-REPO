export function normalizeRecord(record, score) {
    return {
        id: record.id,
        title: record.subject,
        score: Math.round(score ?? 0),
        sessionId: record.session_id,
        member: record.member,
        ministry: record.ministry,
        date: record.created_at,
        itemType: record.item_type,
        snippet: record.full_text,
        fullText: record.full_text,
        status: record.status,
    };
}

export function normalizeSearchResult(result) {
    return {
        rank: result.rank,
        matchedTerms: result.matched_terms ?? [],
        match: normalizeRecord(result.record, result.score),
    };
}

export function normalizeSubmission(record) {
    return {
        id: record.id,
        type: record.item_type,
        sessionId: record.session_id,
        member: record.member,
        ministry: record.ministry,
        subject: record.subject,
        fullText: record.full_text,
        submittedBy: record.member,
        submittedAt: record.created_at,
        status: record.status,
    };
}
