"use client";
import { useState } from "react";

const ALLOWED_TYPES = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
];

const ALLOWED_EXTENSIONS = [".pdf", ".docx", ".txt"];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB

function isAllowedFile(file) {
    if (ALLOWED_TYPES.includes(file.type)) return true;
    const lower = file.name.toLowerCase();
    return ALLOWED_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

export function useDocumentUpload() {
    const [isUploading, setIsUploading] = useState(false);
    const [uploadError, setUploadError] = useState(null);

    const uploadDocument = async (file, itemType = null) => {
        setUploadError(null);

        if (!file) {
            setUploadError("Please select a file to upload.");
            return null;
        }

        if (!isAllowedFile(file)) {
            setUploadError("Only PDF, DOCX and TXT files are supported.");
            return null;
        }

        if (file.size > MAX_FILE_SIZE) {
            setUploadError("File is too large. Maximum size is 10 MB.");
            return null;
        }

        const formData = new FormData();
        formData.append("file", file);
        if (itemType) {
            formData.append("item_type", itemType);
        }

        setIsUploading(true);
        try {
            const response = await fetch("/api/submissions/upload", {
                method: "POST",
                body: formData,
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data.message || "Document upload failed");
            }
            return {
                itemType: data.item_type,
                subject: data.subject,
                fullText: data.full_text,
            };
        } catch (err) {
            setUploadError(err.message || "Document upload failed");
            return null;
        } finally {
            setIsUploading(false);
        }
    };

    return {
        isUploading,
        uploadError,
        uploadDocument,
        clearUploadError: () => setUploadError(null),
    };
}
