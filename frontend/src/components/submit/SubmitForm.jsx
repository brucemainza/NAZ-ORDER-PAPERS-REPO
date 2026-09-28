"use client";
import { useCallback, useRef, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { UploadCloud } from "lucide-react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { Spinner } from "@/components/ui/Spinner";
import { Textarea } from "@/components/ui/Textarea";
import { Toast } from "@/components/ui/Toast";
import { useDocumentUpload } from "@/hooks/useDocumentUpload";
import { useSubmit } from "@/hooks/useSubmit";
import { ZAMBIAN_MINISTRIES } from "@/lib/ministries";

const submitSchema = z
    .object({
        type: z.enum(["Question", "Motion"]),
        sessionId: z.string().min(1, "Please select a parliamentary session"),
        member: z.string().min(3, "Member of Parliament is required"),
        ministry: z.string().optional(),
        answerType: z.enum(["Oral", "Written"]),
        subject: z.string().min(5, "Subject is required"),
        fullText: z.string().min(40, "Full text should provide enough detail for retrieval"),
    })
    .superRefine((values, context) => {
        if (values.type === "Question" && !values.ministry?.trim()) {
            context.addIssue({
                code: z.ZodIssueCode.custom,
                path: ["ministry"],
                message: "Ministry or department is required for questions",
            });
        }
    });

const ALLOWED_UPLOAD_TYPES = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
];

export function SubmitForm({ sessions, itemTypes }) {
    const { error, isSubmitting, submitSubmission } = useSubmit();
    const { isUploading, uploadError, uploadDocument, clearUploadError } = useDocumentUpload();
    const [dragActive, setDragActive] = useState(false);
    const [duplicateInfo, setDuplicateInfo] = useState(null);
    const fileInputRef = useRef(null);

    const {
        register,
        handleSubmit,
        watch,
        setValue,
        formState: { errors },
    } = useForm({
        resolver: zodResolver(submitSchema),
        defaultValues: {
            type: itemTypes[0],
            sessionId: sessions.find((session) => session.status === "Active")?.id ?? "",
            member: "",
            ministry: "",
            answerType: "Oral",
            subject: "",
            fullText: "",
        },
    });

    const selectedType = watch("type");

    const handleUpload = useCallback(
        async (file) => {
            clearUploadError();
            const result = await uploadDocument(file, selectedType);
            if (!result) return;

            if (result.subject) {
                setValue("subject", result.subject, { shouldValidate: true });
            }
            if (result.fullText) {
                setValue("fullText", result.fullText, { shouldValidate: true });
            }
            if (result.itemType && itemTypes.includes(result.itemType)) {
                setValue("type", result.itemType, { shouldValidate: true });
            }
        },
        [clearUploadError, itemTypes, selectedType, setValue, uploadDocument]
    );

    const onDragOver = useCallback((event) => {
        event.preventDefault();
        event.stopPropagation();
        setDragActive(true);
    }, []);

    const onDragLeave = useCallback((event) => {
        event.preventDefault();
        event.stopPropagation();
        setDragActive(false);
    }, []);

    const onDrop = useCallback(
        (event) => {
            event.preventDefault();
            event.stopPropagation();
            setDragActive(false);
            const file = event.dataTransfer.files?.[0];
            if (file) handleUpload(file);
        },
        [handleUpload]
    );

    const onFileInputChange = useCallback(
        (event) => {
            const file = event.target.files?.[0];
            if (file) handleUpload(file);
            event.target.value = "";
        },
        [handleUpload]
    );

    const onSubmit = async (values) => {
        const payload = {
            type: values.type,
            sessionId: values.sessionId,
            member: values.member,
            ministry: values.type === "Question" ? values.ministry : undefined,
            answerType: values.type === "Question" ? values.answerType : undefined,
            subject: values.subject,
            fullText: values.fullText,
        };
        const result = await submitSubmission(payload);
        if (result?.duplicate) {
            setDuplicateInfo({ payload, duplicate: result.duplicate });
        }
    };

    const closeDuplicateModal = useCallback(() => setDuplicateInfo(null), []);

    const submitAnyway = useCallback(async () => {
        if (!duplicateInfo) return;
        const result = await submitSubmission(duplicateInfo.payload, { confirmDuplicate: true });
        if (!result?.duplicate) {
            setDuplicateInfo(null);
        }
    }, [duplicateInfo, submitSubmission]);

    const displayError = error || uploadError;

    return (
        <div className="submit-form">
            <div className="submit-form__workspace">
              <div className="submit-form__grid">
                <fieldset className="submit-form__type">
                    <legend className="submit-form__legend">Item Type</legend>
                    <div className="submit-form__type-options">
                        {itemTypes.map((option) => (
                            <label key={option} className="submit-form__type-option">
                                <input type="radio" value={option} className="submit-form__radio" {...register("type")} />
                                <span>{option}</span>
                            </label>
                        ))}
                    </div>
                </fieldset>

                <Select
                    id="sessionId"
                    label="Parliamentary Session"
                    error={errors.sessionId?.message}
                    {...register("sessionId")}
                >
                    <option value="">Select a session</option>
                    {sessions.map((session) => (
                        <option key={session.id} value={session.id}>
                            {session.name}
                        </option>
                    ))}
                </Select>

                <Input
                    id="member"
                    label="Member of Parliament"
                    placeholder="Hon. Example Member"
                    error={errors.member?.message}
                    {...register("member")}
                />

                {selectedType === "Question" ? (
                    <>
                        <Select id="answerType" label="Answer Type" error={errors.answerType?.message} {...register("answerType")}>
                            <option value="Oral">Oral answer</option>
                            <option value="Written">Written answer</option>
                        </Select>
                        <Select
                            id="ministry"
                            label="Ministry / Department"
                            error={errors.ministry?.message}
                            {...register("ministry")}
                        >
                            <option value="">Select a ministry</option>
                            {ZAMBIAN_MINISTRIES.map((ministry) => (
                                <option key={ministry} value={ministry}>
                                    {ministry}
                                </option>
                            ))}
                        </Select>
                    </>
                ) : (
                    <div className="submit-form__motion-note">Ministry field is not required for motions.</div>
                )}

                <div className="submit-form__wide">
                    <Input
                        id="subject"
                        label="Subject"
                        placeholder="Short, descriptive subject line"
                        error={errors.subject?.message}
                        {...register("subject")}
                    />
                </div>

                <div className="submit-form__wide">
                    <Textarea
                        id="fullText"
                        label="Full Text"
                        placeholder="Enter the full parliamentary question or motion body."
                        error={errors.fullText?.message}
                        {...register("fullText")}
                    />
                </div>
              </div>

              <div className="submit-form__upload-panel">
                <p className="submit-form__legend">Supporting Document</p>
                <div
                    className={`submit-form__upload ${dragActive ? "submit-form__upload--active" : ""}`}
                    onDragOver={onDragOver}
                    onDragLeave={onDragLeave}
                    onDrop={onDrop}
                    role="button"
                    tabIndex={0}
                    aria-label="Upload parliamentary document"
                    onClick={() => fileInputRef.current?.click()}
                    onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            fileInputRef.current?.click();
                        }
                    }}
                >
                    <div className="submit-form__upload-content">
                        {isUploading ? (
                            <>
                                <Spinner />
                                <span>Extracting document text...</span>
                            </>
                        ) : (
                            <>
                                <UploadCloud className="submit-form__upload-icon" aria-hidden="true" />
                                <span className="submit-form__upload-title">Click to upload PDF / DOCX</span>
                                <span className="submit-form__upload-hint">or drag and drop official documents here</span>
                                <span className="submit-form__upload-limit">Maximum size: 20MB</span>
                            </>
                        )}
                    </div>
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept={ALLOWED_UPLOAD_TYPES.join(",")}
                        className="submit-form__upload-input"
                        onChange={onFileInputChange}
                        aria-hidden="true"
                    />
                </div>
              </div>
            </div>

            {displayError ? <Toast variant="error" title="Submission failed" description={displayError} /> : null}

            <div className="submit-form__actions">
                <Button onClick={handleSubmit(onSubmit)} disabled={isSubmitting || isUploading}>
                    {isSubmitting ? (
                        <>
                            <Spinner />
                            Checking similarity...
                        </>
                    ) : (
                        "Submit for review"
                    )}
                </Button>
            </div>

            <Modal
                isOpen={Boolean(duplicateInfo)}
                onClose={closeDuplicateModal}
                title="Possible duplicate detected"
                description="This submission closely matches records already in the system. Review the matches below before continuing."
                footer={
                    <>
                        <Button variant="secondary" onClick={closeDuplicateModal} disabled={isSubmitting}>
                            Cancel
                        </Button>
                        <Button onClick={submitAnyway} disabled={isSubmitting}>
                            {isSubmitting ? "Submitting..." : "Submit anyway"}
                        </Button>
                    </>
                }
            >
                <div className="submit-form__duplicate-matches">
                    {(duplicateInfo?.duplicate.matches ?? []).map((match) => (
                        <div key={`${match.source_record}-${match.rank}`} className="submit-form__duplicate-match">
                            <div className="submit-form__duplicate-match-header">
                                <span className="submit-form__duplicate-match-subject">{match.subject}</span>
                                <span className="submit-form__duplicate-match-score">{Math.round(match.score * 100)}% match</span>
                            </div>
                            <div className="submit-form__duplicate-match-meta">
                                <span>Session: {match.session}</span>
                                <span>Member: {match.member_name}</span>
                            </div>
                            <p className="submit-form__duplicate-match-snippet">{match.snippet}</p>
                            <Link
                                href={`/results/${match.source_record}`}
                                className="submit-form__duplicate-match-link"
                            >
                                View document
                            </Link>
                        </div>
                    ))}
                </div>
            </Modal>
        </div>
    );
}
