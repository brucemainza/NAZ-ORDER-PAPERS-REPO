"use client";
import { X } from "lucide-react";
import { useEffect } from "react";
import { Button } from "@/components/ui/Button";
export function Modal({ isOpen, onClose, title, description, children, footer }) {
    useEffect(() => {
        if (!isOpen) {
            return;
        }
        const handleKeyDown = (event) => {
            if (event.key === "Escape") {
                onClose();
            }
        };
        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [isOpen, onClose]);
    if (!isOpen) {
        return null;
    }
    return (<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/35 px-4">
      <div aria-modal="true" role="dialog" className="w-full max-w-xl rounded-md border border-[--border] bg-white shadow-sm">
        <div className="flex items-start justify-between border-b border-[--border] px-5 py-4">
          <div>
            <h2 className="text-base font-medium text-[--black]">{title}</h2>
            {description ? <p className="mt-1 text-sm text-[--muted]">{description}</p> : null}
          </div>
          <Button aria-label="Close modal" variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4"/>
          </Button>
        </div>
        <div className="px-5 py-4">{children}</div>
        {footer ? <div className="flex items-center justify-end gap-3 border-t border-[--border] px-5 py-4">{footer}</div> : null}
      </div>
    </div>);
}
