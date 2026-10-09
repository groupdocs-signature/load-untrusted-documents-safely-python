# Loading Untrusted Documents Safely in Python

[![Product Page](https://img.shields.io/badge/Product%20Page-2865E0?style=for-the-badge&logo=appveyor&logoColor=white)](https://github.com/groupdocs-signature/GroupDocs.Signature-Docs)
[![Docs](https://img.shields.io/badge/Docs-2865E0?style=for-the-badge&logo=Hugo&logoColor=white)](https://docs.groupdocs.com/signature/python-net/)
[![Blog](https://img.shields.io/badge/Blog-2865E0?style=for-the-badge&logo=WordPress&logoColor=white)](https://blog.groupdocs.com/categories/groupdocs.signature-product-family/)
[![Free Support](https://img.shields.io/badge/Free%20Support-2865E0?style=for-the-badge&logo=Discourse&logoColor=white)](https://forum.groupdocs.com/c/signature/13)
[![Temporary License](https://img.shields.io/badge/Temporary%20License-2865E0?style=for-the-badge&logo=rocket&logoColor=white)](https://purchase.groupdocs.com/temp-license/100124)

## Introduction

Safe document loading is a GroupDocs.Signature behaviour for Python that declines to fetch a document's linked resources while it is being opened. From version 26.9, `LoadOptions.skip_external_resources` defaults to `True`, so a Word file whose picture lives on a remote server renders with an empty placeholder instead of a download.

This repository renders the same DOCX three ways - default, one whitelisted host, everything allowed - and signs it with a QR code without reaching the network at all. `python skip_external_resources_demo.py` prints three byte counts, and the gap between them is the whole argument.

## Use Case Scenarios

A service that accepts document uploads and renders thumbnails. A contract portal that signs files partners send in. An internal tool that previews e-mail attachments. In each case somebody outside your organisation chooses what the document links to, and before 26.9 that meant they also chose which addresses your server would request.

## The Problem

A Word document can hold a picture it does not contain. The file stores an address, and whatever opens it fetches that address. On a desktop this is a feature: the image updates when the source does. On a server accepting uploads it hands the uploader a lever.

The attack has a name, server-side request forgery, and three concrete shapes. An internal address unreachable from the internet is reachable from your server, so a crafted document can make your service fetch `http://169.254.169.254/` or an admin endpoint on localhost. A UNC path can prompt a Windows host to authenticate outbound, handing credentials to a server the attacker controls. And a link to a host that never answers ties up the loading thread until it times out, which is a cheap way to exhaust a worker pool.

### Common Challenges

None of this requires a bug in the document library. Following a link is what the format asks for, so the question is only whether your server should oblige - and the honest difficulty is that the risky behaviour used to be the default, silently, in code that looked completely ordinary.

## The Solution

From 26.9 GroupDocs.Signature does not follow those links unless you say so, and saying so is granular. `whitelisted_resources` names the address fragments that may still be fetched, so a company CDN keeps working while everything else stays blocked. Signing itself never needed the network, which is why an untrusted upload can be signed and stored without a single outbound request.

## Implementation Workflow

Open the document, optionally with a `LoadOptions`; render a preview or sign; compare the output sizes to see what was fetched. The three previews in this sample differ only in the `LoadOptions` passed to the constructor, which is the point - the policy is one object, not a rewrite.

## Requirements

Python 3.9 or later on a 64-bit interpreter, with `groupdocs-signature-net` 26.10.0 from `pip install -r requirements.txt`. The whitelist example needs outbound access to `raw.githubusercontent.com`; without it that preview comes back the same size as the default one and the sample says so rather than failing.

## Project Structure

```
load-untrusted-documents-safely-python/
│
├── skip_external_resources_demo.py
├── requirements.txt
├── documents/
│   └── linked-picture.docx
└── Result/
    ├── preview-default.png
    ├── preview-whitelisted.png
    ├── preview-all.png
    └── signed.docx
```

`documents/linked-picture.docx` is a Word file whose picture is linked rather than embedded, which is what makes the difference measurable. The `Result/` files are committed, so the sizes quoted below can be checked against them rather than taken on trust.

## Practical Examples

### Use Case: Rendering an upload with the safe default

No `LoadOptions` at all, and nothing is fetched.

```python
with signature.Signature(source_path) as sign:
    return save_page_preview(sign, preview_path)
```

The preview shows an empty placeholder where the linked picture would be, and the PNG is correspondingly smaller. Comparing byte sizes is the simplest proof available that no request left the machine.

### Use Case: Allowing one trusted host

When your own documents legitimately point at a company CDN or an internal image server:

```python
load_options = LoadOptions()
load_options.whitelisted_resources = [trusted_address]

with signature.Signature(source_path, load_options) as sign:
    return save_page_preview(sign, preview_path)
```

Matching is a case-insensitive substring test against the resource address, which makes short fragments dangerous: `github` matches `github.attacker.example/payload.png` as happily as the host you meant. Use a scheme, host and path - this sample whitelists `raw.githubusercontent.com/groupdocs-signature/`.

### Use Case: Restoring the old behaviour

```python
load_options = LoadOptions()
load_options.skip_external_resources = False

with signature.Signature(source_path, load_options) as sign:
    return save_page_preview(sign, preview_path)
```

Reserve this for documents your own systems produced. Watch the naming: the obsolete `load_external_resources` property has the opposite polarity, so `skip_external_resources = False` is what replaces `load_external_resources = True`. Copy a value across from the old property and you invert your security posture with nothing to warn you.

### Use Case: Signing a file that arrived from outside

```python
with signature.Signature(source_path) as sign:
    options = QrCodeSignOptions("Approved by GroupDocs.Signature")
    options.encode_type = QrCodeTypes.QR
    options.left = 400
    options.top = 50
    options.width = 120
    options.height = 120

    result = sign.sign(output_path, options)
    return len(result.succeeded)
```

No external resource is requested while the document is loaded, signed or saved. The signed file keeps its link, so a user opening it in Word later still resolves the picture on their own machine - skipping is a server-side policy, not an edit to the document.

### How the preview is written

`PreviewOptions` takes two stream factories rather than a path, which is not obvious from the name:

```python
def create_page_stream(page_data):
    return open(preview_path, "wb")

def release_page_stream(page_data, page_stream):
    page_stream.close()

preview_options = PreviewOptions(create_page_stream, release_page_stream)
preview_options.preview_format = PreviewOptions.PreviewFormats.PNG
sign.generate_preview(preview_options)
```

Plain Python callables work; the binding marshals them. One creates a stream per page, the other releases it. I had expected this to be the awkward part of the port - a .NET delegate with no clean Python equivalent - and it was the one thing that needed no adaptation at all. The sample document has a single page, so one file is written; for multi-page input, put the page number in the file name or every page overwrites the last.

## Benefits

The numbers from the committed `Result/` files, on a one-page DOCX:

| Load mode | Preview | What it means |
|---|---|---|
| default | 16,435 bytes | the picture was never requested |
| whitelisted host | 51,738 bytes | the picture came down from the allowed address |
| all resources | 51,738 bytes | same as whitelisted, since that is the only link |

The linked picture accounts for 35,303 bytes. If your default and whitelisted previews come out the same size, nothing was fetched in either case - which usually means the host is unreachable from that machine rather than that the whitelist failed, and the sample prints a hint saying exactly that.

### Does skipping change the document I sign?

No. The link is preserved in the output; it is simply not followed while your process has the file open. A recipient opening the signed document resolves the picture themselves, exactly as before. That is what makes this safe to apply to files you are handling on someone else's behalf - you are choosing what your server fetches, not editing their document.

## Related Use Cases and Resources

* **Generate Document Pages Preview in Python** - the `PreviewOptions` reference behind the helper above: [Read the article →](https://docs.groupdocs.com/signature/python-net/generate-document-pages-preview/)

* **eSign a Document with a QR-Code Signature** - the signing options used in the last example: [Read the article →](https://docs.groupdocs.com/signature/python-net/esign-document-with-qr-code-signature/)

* **Skipping External Resources in .NET** - the same four operations from the C# side, with the SSRF reasoning: [Read the article →](https://blog.groupdocs.com/signature/skip-external-resources-net/)

## Keywords

`external resources`, `ssrf`, `skip_external_resources`, `whitelisted_resources`, `loadoptions`, `document security`, `untrusted documents`, `linked picture`, `includepicture`, `document preview`, `groupdocs signature`, `python signing`, `qr code signature`, `server-side request forgery`, `unc path`, `svg`, `previewoptions`, `whitelist`, `python via .net`, `26.9`, `docx`, `safe loading`

## Support

For technical support, visit:
- [Free Support Forum](https://forum.groupdocs.com/c/signature/13)
- [Product Documentation](https://docs.groupdocs.com/signature/python-net/)
- [Get Temporary License](https://purchase.groupdocs.com/temp-license/100124)
