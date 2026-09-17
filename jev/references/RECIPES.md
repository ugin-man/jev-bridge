# Reusable patterns

Examples are not a list of supported industries. Keep the user's task and stack.

- Compare related records together; separate mismatches from missing evidence.
- Ask independent verification questions together; use Noul per independently
  applicable label rather than forcing multi-label data into one Choice.
- Rank items with comparable Score questions, retaining raw dimensions for changes
  in weights without rerunning the model.
- Build candidates from observed values/spans/actions, then let Choice select one.
  Do not invent missing candidate values or treat a selection as action permission.
- Route uncertain or unsupported situations only when the user's workflow calls for
  that; do not apply a global confidence cutoff to every harmless choice.

Assets include a smoke request, product-pair comparison, and reusable support
questions/data. Their language and domain do not constrain new requests.

For a new task, consult the official TypeSafe skill and closest live cookbook.
Question design is part of the host's reasoning, not a required form for the user.
