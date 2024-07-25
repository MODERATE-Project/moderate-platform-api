import { Link, RichTextEditor } from "@mantine/tiptap";
import TextAlign from "@tiptap/extension-text-align";
import { EditorOptions, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import _ from "lodash";
import { useEffect, useMemo } from "react";

export const RichEditor: React.FC<{
  editorProps?: Partial<EditorOptions>;
  onUpdate?: EditorOptions["onUpdate"];
  content?: string;
}> = function ({ editorProps, onUpdate, content }) {
  const mergedEditorProps = useMemo(() => {
    const { extensions, ...filteredEditorProps } = editorProps ?? {};
    extensions && console.debug("Ignored extensions:", extensions);

    const baseEditorProps = {
      extensions: [
        StarterKit,
        Link,
        TextAlign.configure({ types: ["heading", "paragraph"] }),
      ],
    };

    if (onUpdate) {
      Object.assign(baseEditorProps, { onUpdate });
    }

    return _.merge(baseEditorProps, filteredEditorProps);
  }, [editorProps, onUpdate]);

  const editor = useEditor(mergedEditorProps);

  useEffect(() => {
    if (content && editor) {
      editor.commands.setContent(content);
    }
  }, [content, editor]);

  return (
    <RichTextEditor editor={editor}>
      <RichTextEditor.Toolbar sticky stickyOffset={60}>
        <RichTextEditor.ControlsGroup>
          <RichTextEditor.Bold />
          <RichTextEditor.Italic />
          <RichTextEditor.Strikethrough />
          <RichTextEditor.ClearFormatting />
          <RichTextEditor.Code />
        </RichTextEditor.ControlsGroup>

        <RichTextEditor.ControlsGroup>
          <RichTextEditor.H1 />
          <RichTextEditor.H2 />
          <RichTextEditor.H3 />
          <RichTextEditor.H4 />
        </RichTextEditor.ControlsGroup>

        <RichTextEditor.ControlsGroup>
          <RichTextEditor.Blockquote />
          <RichTextEditor.Hr />
          <RichTextEditor.BulletList />
          <RichTextEditor.OrderedList />
        </RichTextEditor.ControlsGroup>

        <RichTextEditor.ControlsGroup>
          <RichTextEditor.Link />
          <RichTextEditor.Unlink />
        </RichTextEditor.ControlsGroup>

        <RichTextEditor.ControlsGroup>
          <RichTextEditor.AlignLeft />
          <RichTextEditor.AlignCenter />
          <RichTextEditor.AlignJustify />
          <RichTextEditor.AlignRight />
        </RichTextEditor.ControlsGroup>
      </RichTextEditor.Toolbar>

      <RichTextEditor.Content />
    </RichTextEditor>
  );
};
