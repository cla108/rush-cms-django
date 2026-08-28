

/**
 * Run a callback when triggered. But only after a period of time, so multiple signals can be grouped together.
 */
export class ThrottledSignalReceiver {

  private shouldTrigger: boolean;

  constructor(pollMillis: number, callback: () => void) {
    this.shouldTrigger = false;
    const onPoll = () => {
      if (this.shouldTrigger){
        callback();
        this.shouldTrigger = false;
      }
      setTimeout(onPoll, pollMillis);
    };
    onPoll();
  }

  public trigger(): void {
    this.shouldTrigger = true;
  }

}


/**
 * A promise that resolves immediately if the given HTMLElement exists in the DOM 
 * already, or otherwise when the DOM element is added the future.
 * @param id the id of the DOM element to look for.
 * @returns a Promise containing the HTMLElement once it's been located.
 */
export function waitForElementById(id: string): Promise<HTMLElement> {
  return new Promise((resolve) => {

    const resolveIfFound = () => {
      const element = document.getElementById(id);
      if (element) {
        return resolve(element);
      }
    };

    // Return if the element already exists.
    resolveIfFound();

    // Otherwise create an observer to listen for DOM changes.
    const observer = new MutationObserver(resolveIfFound);
    observer.observe(document.body, { childList: true, subtree: true });

  });
}

/**
 * Find the expected element by ID in the DOM, or throw an Error if it could not be found.
 */
export function expectEl(id: string): HTMLElement {
  const el = document.getElementById(id);
  if (el === null) {
    throw new Error("Expected DOM element with id '" + id + "' to exist!");
  }
  return el;
}

/**
 * Find and return the first element matching against the provided selector, or 
 * throw an error if the element couldn't be found.
 * @param element the element to run a selector on.
 * @param selector the selector string to check against.
 */
export function expectQuerySelector(element: HTMLElement | Document, selector: string): HTMLElement {
  const el = element.querySelector(selector);
  if (el === null || !(el instanceof HTMLElement)) {
    throw new Error("Expected HTML DOM element matching '" + selector + "' to exist as a child of '" + element + "'!");
  }
  return el;
}

export function htmlElementQuerySelectAll(element: HTMLElement | Document, selector: string): Array<HTMLElement> {
  const els = element.querySelectorAll(selector);
  const arr = [];
  for (let el of els){
    if (el instanceof HTMLElement){
      arr.push(el);
    }
  }
  return arr;
}
