    // Generate QR code with text value using a QR code generator library
    const qrCodeImage = document.getElementById("qr-code-image");
    const invoice = qrCodeImage.getAttribute('invoice');
    qrCodeImage.src = `https://jukebox.lighting/api/v1/qrcode/${encodeURIComponent(invoice)}`;
    
    // Add event listener to copy invoice button
    const copyInvoiceButton = document.querySelector(".copy-invoice");
    copyInvoiceButton.addEventListener("click", () => {
      // Copy text value to clipboard
      const tempElement = document.createElement("textarea");
      tempElement.value = invoice;
      document.body.appendChild(tempElement);
      tempElement.select();
      document.execCommand("copy");
      document.body.removeChild(tempElement);
    });

    qrCodeImage.addEventListener("click", () => {
      window.location.replace('lightning:${encodeURIComponent(invoice)}');
    });
