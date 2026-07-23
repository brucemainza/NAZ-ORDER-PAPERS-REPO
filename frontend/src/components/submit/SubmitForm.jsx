"use client";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Spinner } from "@/components/ui/Spinner";
import { Textarea } from "@/components/ui/Textarea";
import { Toast } from "@/components/ui/Toast";
import { useSubmit } from "@/hooks/useSubmit";
const submitSchema = z
    .object({
    type: z.enum(["Question", "Motion"]),
    sessionId: z.string().min(1, "Please select a parliamentary session"),
    member: z.string().min(3, "Member of Parliament is required"),
    ministry: z.string().optional(),
    subject: z.string().min(5, "Subject is required"),
    fullText: z.string().min(40, "Full text should provide enough detail for retrieval"),
})
    .superRefine((values, context) => {
    var _a;
    if (values.type === "Question" && !((_a = values.ministry) === null || _a === void 0 ? void 0 : _a.trim())) {
        context.addIssue({
            code: z.ZodIssueCode.custom,
            path: ["ministry"],
            message: "Ministry or department is required for questions",
        });
    }
});
export function SubmitForm({ sessions }) {
    var _a, _b, _c, _d, _e, _f, _g;
    const { error, isSubmitting, submitSubmission } = useSubmit();
    const { register, handleSubmit, watch, formState: { errors }, } = useForm({
        resolver: zodResolver(submitSchema),
        defaultValues: {
            type: "Question",
            sessionId: (_b = (_a = sessions.find((session) => session.status === "Active")) === null || _a === void 0 ? void 0 : _a.id) !== null && _b !== void 0 ? _b : "",
            member: "",
            ministry: "",
            subject: "",
            fullText: "",
        },
    });
    const selectedType = watch("type");
    const onSubmit = async (values) => {
        await submitSubmission({
            type: values.type,
            sessionId: values.sessionId,
            member: values.member,
            ministry: values.type === "Question" ? values.ministry : undefined,
            subject: values.subject,
            fullText: values.fullText,
        });
    };
    return (<div className="submit-form">
      <div className="submit-form__grid">
        <fieldset className="submit-form__type">
          <legend className="submit-form__legend">Item Type</legend>
          <div className="submit-form__type-options">
            {["Question", "Motion"].map((option) => (<label key={option} className="submit-form__type-option">
                <input type="radio" value={option} className="submit-form__radio" {...register("type")}/>
                <span>{option}</span>
              </label>))}
          </div>
        </fieldset>

        <Select id="sessionId" label="Parliamentary Session" error={(_c = errors.sessionId) === null || _c === void 0 ? void 0 : _c.message} {...register("sessionId")}>
          <option value="">Select a session</option>
          {sessions.map((session) => (<option key={session.id} value={session.id}>
              {session.name}
            </option>))}
        </Select>

        <Input id="member" label="Member of Parliament" placeholder="Hon. Example Member" error={(_d = errors.member) === null || _d === void 0 ? void 0 : _d.message} {...register("member")}/>

        {selectedType === "Question" ? (<Input id="ministry" label="Ministry / Department" placeholder="Ministry of Health" error={(_e = errors.ministry) === null || _e === void 0 ? void 0 : _e.message} {...register("ministry")}/>) : (<div className="submit-form__motion-note">
            Ministry field is not required for motions.
          </div>)}

        <div className="submit-form__wide">
          <Input id="subject" label="Subject" placeholder="Short, descriptive subject line" error={(_f = errors.subject) === null || _f === void 0 ? void 0 : _f.message} {...register("subject")}/>
        </div>

        <div className="submit-form__wide">
          <Textarea id="fullText" label="Full Text" placeholder="Enter the full parliamentary question or motion body." error={(_g = errors.fullText) === null || _g === void 0 ? void 0 : _g.message} {...register("fullText")}/>
        </div>
      </div>

      <Toast variant="info" title="Similarity review will run automatically" description="The submission will be checked against historical records before you land on the result review screen."/>
      {error ? <Toast variant="error" title="Submission failed" description={error}/> : null}

      <div className="submit-form__actions">
        <Button onClick={handleSubmit(onSubmit)} disabled={isSubmitting}>
          {isSubmitting ? (<>
              <Spinner />
              Checking similarity...
            </>) : ("Submit for review")}
        </Button>
      </div>
    </div>);
}
