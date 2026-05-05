export const copyToClipboard = (text: string) => {
  navigator.clipboard.writeText(text).then(() => {
    // Optionally handle success (toast, etc)
  }).catch(err => {
    console.error('Could not copy text: ', err);
  });
};
