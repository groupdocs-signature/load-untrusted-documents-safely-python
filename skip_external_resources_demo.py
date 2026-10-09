# Topic: Load documents safely - external resources are skipped by default since 26.9.
# Uses GroupDocs.Signature for Python via .NET: LoadOptions.skip_external_resources and
# LoadOptions.whitelisted_resources decide which linked pictures may be fetched.

import os
import sys

import groupdocs.signature as signature
from groupdocs.signature.domain import QrCodeTypes
from groupdocs.signature.options import LoadOptions, PreviewOptions, QrCodeSignOptions

DOCS = "documents"
RESULT = "Result"

# The picture in this document is linked to an image on GitHub, not embedded.
SOURCE_DOCX = os.path.join(DOCS, "linked-picture.docx")

# Only addresses that contain this text are loaded in the whitelist example.
TRUSTED_ADDRESS = "https://raw.githubusercontent.com/groupdocs-signature/"


def apply_license() -> None:
    # Point this at your .lic file to remove evaluation limits.
    # Get a free temporary licence: https://purchase.groupdocs.com/temporary-license
    license_path = "REPLACE_WITH_YOUR_LICENSE_PATH"
    if os.path.exists(license_path):
        signature.License().set_license(license_path)
        print("[license] applied")
    else:
        print("[license] no licence set - running in evaluation mode")


def preview_with_default_settings(source_path: str, preview_path: str) -> int:
    """
    Generates a page preview of a document with the default load settings.

    Remarks:
        Opens the document with Signature and no LoadOptions. Since GroupDocs.Signature
        26.9, LoadOptions.skip_external_resources is True by default: linked pictures,
        INCLUDEPICTURE fields, linked pictures in presentations and spreadsheets, and the
        images and style sheets of SVG files are not requested, so the preview shows an
        empty placeholder instead of the picture. Embedded pictures are not affected.
        This is the safe default for documents that arrive from users, e-mail or partner
        systems: a crafted document cannot make your server call internal addresses
        (server-side request forgery), leak Windows credentials through a UNC path, or
        wait for an unreachable host. Writes a PNG preview to preview_path and returns
        its size in bytes.
    """
    with signature.Signature(source_path) as sign:
        return save_page_preview(sign, preview_path)


def preview_with_whitelisted_host(source_path: str, preview_path: str,
                                  trusted_address: str) -> int:
    """
    Generates a page preview that loads external resources from trusted addresses only.

    Remarks:
        Passes a LoadOptions carrying whitelisted_resources to the Signature
        constructor. External resources stay skipped, except those whose address
        contains one of the listed fragments, compared ignoring case. Prefer long
        fragments such as a scheme, host and path: a short one like "github" would also
        match an attacker's address that merely contains that word. Use this when your
        own documents legitimately link to a company CDN or an internal image server.
        Writes a PNG preview containing the linked picture to preview_path and returns
        its size in bytes. The machine needs access to the trusted host; without it the
        preview comes back the same size as the default one.
    """
    load_options = LoadOptions()
    load_options.whitelisted_resources = [trusted_address]

    with signature.Signature(source_path, load_options) as sign:
        return save_page_preview(sign, preview_path)


def preview_with_all_external_resources(source_path: str, preview_path: str) -> int:
    """
    Generates a page preview that loads every external resource a document links to.

    Remarks:
        Sets skip_external_resources to False, restoring the behaviour of versions
        before 26.9: every linked picture and style sheet is requested while the
        document is loaded. Use it only for documents you trust, such as files your own
        application produced. Watch the naming - the obsolete load_external_resources
        property has the opposite polarity, so skip_external_resources = False is what
        replaces load_external_resources = True, and copying a value across from the old
        property inverts your intent with no error to warn you. Writes a PNG preview to
        preview_path and returns its size in bytes.
    """
    load_options = LoadOptions()
    load_options.skip_external_resources = False

    with signature.Signature(source_path, load_options) as sign:
        return save_page_preview(sign, preview_path)


def sign_untrusted_document(source_path: str, output_path: str) -> int:
    """
    Signs an untrusted Word document without fetching anything it links to.

    Remarks:
        Opens the document with the default load settings and adds a QR-code signature
        through QrCodeSignOptions. No external resource is requested while the document
        is loaded, signed or saved, and the signed document keeps its link, so an
        application that opens it later can still resolve the picture itself. Skipping is
        a server-side policy rather than an edit to the document, which is what makes it
        safe to apply to files handled on someone else's behalf. This is the typical flow
        for signing uploads. Writes the signed DOCX to output_path and returns the number
        of signatures added.
    """
    with signature.Signature(source_path) as sign:
        options = QrCodeSignOptions("Approved by GroupDocs.Signature")
        options.encode_type = QrCodeTypes.QR
        options.left = 400
        options.top = 50
        options.width = 120
        options.height = 120

        result = sign.sign(output_path, options)
        return len(result.succeeded)


def save_page_preview(sign: "signature.Signature", preview_path: str) -> int:
    # The sample document has one page, so the page preview goes to one file.
    # PreviewOptions takes two stream factories rather than a path: one to create a
    # stream per page, one to release it. For multi-page input, put the page number in
    # the file name or every page overwrites the last.
    def create_page_stream(page_data):
        return open(preview_path, "wb")

    def release_page_stream(page_data, page_stream):
        page_stream.close()

    preview_options = PreviewOptions(create_page_stream, release_page_stream)
    preview_options.preview_format = PreviewOptions.PreviewFormats.PNG

    sign.generate_preview(preview_options)
    return os.path.getsize(preview_path) if os.path.exists(preview_path) else 0


def main() -> int:
    os.makedirs(DOCS, exist_ok=True)
    os.makedirs(RESULT, exist_ok=True)
    apply_license()

    if not os.path.exists(SOURCE_DOCX):
        print(f"Missing source document: {os.path.abspath(SOURCE_DOCX)}", file=sys.stderr)
        return 1

    default_preview = os.path.join(RESULT, "preview-default.png")
    trusted_preview = os.path.join(RESULT, "preview-whitelisted.png")
    all_preview = os.path.join(RESULT, "preview-all.png")
    signed_docx = os.path.join(RESULT, "signed.docx")

    default_size = preview_with_default_settings(SOURCE_DOCX, default_preview)
    print(f"Default settings   : {default_size} bytes, picture skipped")

    trusted_size = preview_with_whitelisted_host(
        SOURCE_DOCX, trusted_preview, TRUSTED_ADDRESS)
    print(f"Whitelisted address: {trusted_size} bytes")

    all_size = preview_with_all_external_resources(SOURCE_DOCX, all_preview)
    print(f"All resources      : {all_size} bytes")

    if trusted_size == default_size:
        print("The linked picture could not be downloaded.")
        print("Check the internet access to raw.githubusercontent.com.")

    added = sign_untrusted_document(SOURCE_DOCX, signed_docx)
    print(f"Signatures added without loading external resources: {added}")
    print(f"Results: {os.path.abspath(RESULT)}")

    return 0 if added == 1 else 2


if __name__ == "__main__":
    sys.exit(main())
