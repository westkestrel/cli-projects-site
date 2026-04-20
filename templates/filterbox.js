/**
 * Filterbox allows you to use checkboxes to show and hide rows of data.
 *
 * To use it, you ensure that your HTML has a controls block. Note that if you omit the
 * id="" and for="" tags on the input and label, they will be inferred from the
 * label contents.  In the code below
 * - the first checkbox toggles "cats" (despite the label being "Felines")
 * - the second toggles "dogs" (inferred from the label)
 * - the third toggles "bugs", and ignores the explanatory text after the colon
 * - the fourth toggles "bugs", and ignores the explanatory text in parenthesis
 * - the fifth toggles "eight-legs" (8 became eight since CSS class names cannot begin with digits)
 * - the sixth toggles "birds-and-bees" (spaces become hyphens)
 * - the seventh toggles both "birds" and "Bees" (commas separate items)
 *
 * <ul class="filterbox-controls filter-animals">
 * <li><input type="checkbox" id="cats"><label for="cats">Felines</label></li>
 * <li><input type="checkbox"><label>Dogs</label></li>
 * <li><input type="checkbox"><label>Bugs: six-legged beasties</label></li>
 * <li><input type="checkbox"><label>Bugs (six-legged beasties)</label></li>
 * <li><input type="checkbox"><label>8-Legs (arachnids and octopi)</label></li>
 * <li><input type="checkbox"><label>Birds and Bees</label></li>
 * <li><input type="checkbox"><label>Birds, Bees</label></li>
 * </ul>
 *
 * Your HTML also must have a data block:
 *
 * <table class="filterbox-data filter-animals">
 * <th>...</th>
 * <tr class="cats">...</tr>
 * <tr class="cats">...</tr>
 * <tr class="dogs">...</tr>
 * <tr class="bugs">...</tr>
 * <tr class="eight-legs">...</tr>
 * <tr class="birds">...</tr>
 * <tr class="bees">...</tr>
 * <tr class="birds-and-bees">...</tr>
 * </table>
 *
 * When the user toggles the checkbox for a given id, all data elements with that
 * CSS class have their visibility toggled. In the case above if the user toggles
 * the last checkbox both the "birds" and "bees" rows will be hidden, but not the
 * "birds-and-bees" row.
 */
 
const filterboxBootstrap = () => {

const digitsToWords = (text) => {
    return text
        .replace('0', 'zero-')
        .replace('1', 'one-')
        .replace('2', 'two-')
        .replace('3', 'three-')
        .replace('4', 'four-')
        .replace('5', 'five-')
        .replace('6', 'six-')
        .replace('7', 'seven-')
        .replace('8', 'eight-')
        .replace('9', 'nine-')
}

const setVisibility = (filterType, filterClassName, flag) => {
    const targetClassName = `filterbox-data ${filterType}`
    const filterContainers = document.getElementsByClassName(targetClassName)
    if (!filterContainers.length) {
        console.error(`no element with class="${targetClassName}"`)
        return
    }
    for (container of filterContainers) {
        for (filterValue of filterClassName.split(' ')) {
            filterValue = digitsToWords(filterValue)
            const className = container.getAttribute('class') || ''
            const hiddenPart = `hide-${filterValue}`
            const parts = className.split(' ').filter(x => x != hiddenPart)
            if (!flag) {
                parts.push(hiddenPart)
            }
            container.setAttribute('class', parts.join(' '))
        }
    }
}

const wireUpCheckboxes = () => {
    const cssRules = []
    const filters = document.getElementsByClassName('filterbox-controls')
    var metaKey = false
    var justPerformedLongPress = false
    var timeout = null
    const hit = event => {
        metaKey = event.metaKey
        justPerformedLongPress = false
        if (timeout) clearTimeout(timeout)
        timeout = setTimeout(longPress, 1000, event)
        return false
    }
    const release = event => {
        metaKey = event.metaKey
        if (timeout) {
            clearTimeout(timeout)
            tiemout = null
        }
        return false
    }
    const getHtmlFor = node => {
        if (!node) return null
        const id = node.getAttribute('for')
        if (id) return id
        return getHtmlFor(node.parentNode)
    }
    const longPress = event => {
        timeout = null
        metaKey = true
        const htmlFor = getHtmlFor(event.target)
        const checkbox = htmlFor ? document.getElementById(htmlFor) : event.target
        if (!checkbox) {
            console.error('no checkbox is associated with the event', event)
            return false
        }
        checkbox.checked = !checkbox.checked
        const changeEvent = new Event('change')
        changeEvent.target = checkbox
        checkbox.dispatchEvent(changeEvent)
        justPerformedLongPress = true
        return false
    }
    for (filter of filters) {
        const filterType = filter.getAttribute('class').split(' ').filter(x => x.startsWith('filter-'))[0]
        if (!filterType) {
            console.error('filterbox-controls lacks a filter-TYPE class:', filter)
            continue
        }
        const toggles = filter.getElementsByTagName('input')
        for (toggle of toggles) {
            const toggleId = toggle.getAttribute('id')
            const label = toggle.nextElementSibling
            const filterValues = toggleId
                ? [toggleId]
                : label.innerHTML
                    .replace(/<span class="text">(.*?)<\/span>\s*/m, '$1')
                    .replace(/<span class="icon">(.*?)<\/span>\s*/m, '')
                    .toLocaleLowerCase()
                    .replace(/ *[(].*[)]/, '')
                    .replace(/:.*/, '')
                    .split(/, */)
                    .map(x => x.replace(/\W+/g, ' ').trim().replace(/ /g, '-'))
            const filterId = `${filterType}-${filterValues.join('-')}`
            const filterClassName = filterValues.join(' ')
            if (!toggleId) { toggle.setAttribute('id', filterId) }
            if (!toggle.getAttribute('class')) { toggle.setAttribute('class', filterClassName) }
            const stateChange = event => {
                if (justPerformedLongPress) {
                    event.target.checked = !event.target.checked
                    justPerformedLongPress = false
                    return // if we just toggled state due to long press, do NOT re-toggle it for the button-release
                }
                if (metaKey) {
                    // if the user command-clicks on a checkbox we have custom selection behaviour
                    // - if any other checkbox is selected, we "solo" the clicked checkbox,
                    //   selecting it and deselecting all others.
                    // - if the element is presently soloed, we select ALL checkbox,
                    //   including the one that was just checked.
                    // In other words, command-clicking an element shows only its items.
                    // Command-clicking again undoes this and shows everything.
                    const wasChecked = event.target.checked
                    var anyOthersWereChecked = false
                    for (t of toggles) {
                        if (t.getAttribute('id') != event.target.getAttribute('id')) {
                            anyOthersWereChecked = anyOthersWereChecked || t.checked
                        }
                    }
                    console.log('anyOthersWereChecked', anyOthersWereChecked)
                    for (t of toggles) {
                        if (t.getAttribute('id') != event.target.getAttribute('id')) {
                            t.checked = !anyOthersWereChecked
                            setVisibility(filterType, t.getAttribute('class'), !anyOthersWereChecked)
                        } else {
                            t.checked = true
                            setVisibility(filterType, filterClassName, true)
                        }
                    }
                } else {
                    setVisibility(filterType, filterClassName, event.target.checked)
                }
            }
            label.setAttribute('for', toggleId || filterId)
            toggle.addEventListener('mousedown', hit)
            toggle.addEventListener('mouseup', release)
            label.addEventListener('mousedown', hit)
            label.addEventListener('mouseup', release)
            toggle.addEventListener('touchstart', hit)
            toggle.addEventListener('touchend', release)
            label.addEventListener('touchstart', hit)
            label.addEventListener('touchend', release)
            toggle.addEventListener('change', stateChange)
            toggle.checked = true
            for (filterValue of filterValues) {
                filterValue = digitsToWords(filterValue)
                cssRules.push(`.filterbox-data.${filterType}.hide-${filterValue} .${filterValue} { display: none }`)
            }
        }
    }
    const head = document.getElementsByTagName('head')[0]
    const style = document.createElement('style')
    style.setAttribute('type', 'text/css')
    style.innerHTML = cssRules.join('\n')
    head.appendChild(style)
}

window.addEventListener('load', wireUpCheckboxes)
 
}
filterboxBootstrap()
