---
paths:
  - "app/assets/**/*.css"
  - "app/assets/**/*.vue"
---

# CSS

## Units

Use `rlh` as the base unit. Do not use pixels.

## Property order

Write properties within a rule in alphabetical order.

## Architecture

CSS follows CUBE CSS (composition, utility, block, exception). The files are in `app/assets/css/`.

- Composition: layout between elements comes from the classes in `compositions/` (`.cluster`, `.repel`, `.stack`, `.with-sidebar`). A block does not declare `display: flex` and `gap` itself when a composition provides that layout. The gap of a composition is chosen with its size modifier (`.stack--tiny`, `.cluster--tiny`), which follows the scale of the spacing utilities; a block does not set the gap custom property itself.
- Utility: a single property that recurs across blocks, such as muted colour, small font size or a plain list, comes from the `u-` classes in `utilities/`. Before writing such a property into a block, check whether a utility exists; if the same property set appears in two blocks, add a utility.
- Block: each component has one block class with BEM-style element classes (`.entity-register-row__name`) in its own file in `components/`. The block contains only what is specific to the component. Elements with identical styles share one element class (`__action` for the edit and delete buttons, not `__edit` and `__delete`).
- Exception: a state or variant of a block is expressed as a `data-*` attribute selector (`.note[data-level="warning"]`), not as a modifier class.

Rules that `elements.css` already sets, such as `margin: 0` on `p`, are not repeated in a block. Tests select elements by role or `aria-label` where possible, not by styling classes.

Example, `entity_register_row.vue`:

```html
<li class="entity-register-row">
    <div class="cluster cluster--tiny entity-register-row__head">
        <p class="entity-register-row__name">…</p>
        <button class="icon-button entity-register-row__action">…</button>
    </div>
    <p class="u-color-muted u-font-small">…</p>
    <ul class="u-list-plain entity-register-row__mentions">…</ul>
</li>
```
