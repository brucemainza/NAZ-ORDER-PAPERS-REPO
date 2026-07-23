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
    return (<div className="ui-modal">
      <div aria-modal="true" role="dialog" className="ui-modal__dialog">
        <div className="ui-modal__header">
          <div>
            <h2 className="ui-modal__title">{title}</h2>
            {description ? <p className="ui-modal__description">{description}</p> : null}
          </div>
          <Button aria-label="Close modal" variant="ghost" size="sm" onClick={onClose}>
            <X className="ui-modal__close-icon"/>
          </Button>
        </div>
        <div className="ui-modal__body">{children}</div>
        {footer ? <div className="ui-modal__footer">{footer}</div> : null}
      </div>
    </div>);
}
