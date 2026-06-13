export default {
    props: ["type"],
    template: `
    <article :class="'message message--' + type">
      <div class="message__body u-ll">
        <slot></slot>
      </div>
    </article>
  `,
};
