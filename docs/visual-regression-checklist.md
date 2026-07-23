# UI Visual Regression Checklist

Use this checklist with `npm run test:e2e` while migrating each component away
from Tailwind. Reference screenshots are stored beside the Playwright test.

## Automated Checks

- Desktop login at 1440 x 900.
- Mobile login at 390 x 844.
- Desktop dashboard, submission form, record list, reports, sessions, users,
  record detail, and audit pages.
- Mobile authenticated dashboard.
- Animations disabled for deterministic screenshots.
- Dynamic audit-table contents masked while its surrounding layout remains
  compared.

## Manual Interaction Checks

- Login validation, password visibility toggle, submit state, and error message.
- Sidebar active item, links, and logout button.
- Buttons: default, hover, focus, active, and disabled states.
- Inputs, selects, and textareas: placeholder, focus, validation error, and
  disabled states.
- Submission question/motion radio controls and conditional ministry field.
- Search filters, pagination, expandable record text, and empty/loading states.
- Review decision radios, candidate selector, notes field, save state, and toast.
- Modal open/close button and Escape-key close behavior.
- Tables at narrow widths retain horizontal scrolling.
- Desktop breakpoints at 768, 1024, and 1280 pixels.
- Mobile page layout has no unintended horizontal document overflow.
